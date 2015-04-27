#!/usr/bin/perl -w
#nom.cgi
=begin comment

For doing traffic logging site-wide.
Sets and reads cookies and logs to visit database

Note:
This script has two functions and is hopefully run twice per page to do these
two different things. First, it is loaded normally and does the majority of the
logging and cookie-ing. Then if the user has Javascript enabled, the page loads
the script again, sending it the referrer information. At that time, all this
script does is append the referrer information to the previously logged data.
(explanation: Because this is being loaded by the page the user is on, it is
one link removed from the actual page of interest. So the referrer this script
detects is the actual page of interest and it cannot detect the actual
referrer. So Javascript is needed to pass that information to this script.)

=end comment
=cut
use strict;
use CGI;
use CGI::Cookie;
use lib 'code';
use DBIconnect;
use Traffic;
use Randchar;

# Constants
my $COOKIE_NAME = "visitors_v1";
my $CONFIG_FILE = "/var/www/nsto.co/protect/dbi_config.ini";
my $CONFIG_SECTION = "Tracker";

# Set up CGI and DBI objects
my $cgi = new CGI;
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Check query string to see if it's the second (Javascript) invocation
my $loading = $cgi->url_param('l');
my $referrer = $cgi->url_param('r');
if ($loading) {
	if ($referrer) {
		if (my $visit_id = find_entry($dbh, $cgi, $COOKIE_NAME)) {
			add_referrer($dbh, $visit_id, $referrer);
		}
	}
	$dbh->disconnect();
	print $cgi->header('text/css');
	exit;
}


# set cookie
my $cookie_value = get_cookie($COOKIE_NAME);
unless ($cookie_value) {
	if ($ENV{HTTP_HOST} =~ m/([^.]+\.[^.]+)$/) {
		$cookie_value = set_cookie($COOKIE_NAME, $1);
	}
}

# Print 'stylesheet'
print $cgi->header('text/css');



# Get visit data
my $dataref = get_data_secondary($cgi);
$$dataref{cookie} = $cookie_value;

# Add visit entry to MySQL
my $visitor_id = add_visitor_db($dbh, $dataref);
add_visit_db($dbh, $dataref, $visitor_id);

# Disconnect from database
$dbh->disconnect();




#################### SUBROUTINES ####################

# Pack up a %data hash with visit information.
# Note: Because this script is being loaded by the page of interest, the
# referrer will be the actual page the user is on.
sub get_data_secondary {
	
	my ($cgi) = @_;
	
	my %data;
	
	$data{unix_time} = time;
	$data{ip} = $cgi->remote_addr();
	$data{page} = $cgi->referer();
	$data{user_agent} = $cgi->user_agent();
	
	return \%data;
}

# Finds the most recent entry in the last 15 seconds with the same ip,
# user_agent, cookie, current page, and no referrer. Returns the visit_id.
sub find_entry {
	
	my ($dbh, $cgi, $cookie_name) = @_;
	
	my $SEARCH_BACK = 15; #seconds
	
	my %data;
	
	$data{unix_time} = time;
	$data{ip} = $cgi->remote_addr();
	$data{user_agent} = $cgi->user_agent();
	$data{page} = $cgi->referer();
	$data{cookie} = get_cookie($cookie_name);
	
	
	# Assemble select statement
	
	my $select_command = qq{
		SELECT vt.visit_id
		FROM visits vt
		JOIN visitors vtr ON vt.visitor_id = vtr.visitor_id
		WHERE vt.unix_time > ? AND vtr.ip = ? AND vtr.user_agent = ?
			AND vt.page = ? AND vt.referrer IS NULL AND
	};
	
	if ($data{cookie}) {
		$select_command .= " cookie = ? ";
	} else {
		$select_command .= " cookie IS NULL ";
	}
	
	$select_command .= qq{
		ORDER BY vt.visit_id DESC
		LIMIT 1 ;
	};
	
	
	# Execute statement, return result
	
	my $dsh = $dbh->prepare($select_command);
	if ($data{cookie}) {
		$dsh->execute(
			$data{unix_time} - $SEARCH_BACK,
			$data{ip},
			$data{user_agent},
			$data{page},
			$data{cookie},
		);
	} else {
		$dsh->execute(
			$data{unix_time} - $SEARCH_BACK,
			$data{ip},
			$data{user_agent},
			$data{page},
		);
	}
	
	if (my $visit_id = $dsh->fetchrow_array) {
		return $visit_id;
	} else {
		return;
	}
}

# Add referrer to visit entry in database
sub add_referrer {
	
	my ($dbh, $visit_id, $referrer) = @_;
	
	my $select_command = qq{
		UPDATE visits
		SET referrer = ?
		WHERE visit_id = ? ;
	};
	
	my $dsh = $dbh->prepare($select_command);
	
	$dsh->execute($referrer, $visit_id);
	
	return;
}