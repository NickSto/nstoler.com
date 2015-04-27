#!/usr/bin/perl -w
#Traffic.pm
=begin comment

Useful subroutines for doing traffic logging from any random CGI script.

If the visit results in HTML (via a .tmpl or .html file), this should all be
handled by nom.cgi. As of this writing, this is just for scripts which are
visited and do something other than print a template.

Examples: /misc/export_visits.cgi, /s/contact/send.cgi

=end comment
=cut
use strict;
use CGI;
use CGI::Cookie;
use Randchar;
use DBIconnect;

# Constants
my $COOKIE_NAME = "visitors_v1";
my $CONFIG_FILE = "/var/www/nsto.co/protect/dbi_config.ini";
my $CONFIG_SECTION = "Tracker";

sub add_visit {
	add_visit_plain();
}

sub add_visit_plain {

	# Set up CGI and DBI objects
	my $cgi = new CGI;
	my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

	# set cookie if needed
	my $cookie_value = get_cookie($COOKIE_NAME);
	unless ($cookie_value) {
		if ($ENV{HTTP_HOST} =~ m/([^.]+\.[^.]+)$/) {
			$cookie_value = set_cookie($COOKIE_NAME, $1);
		}
	}

	# Get visit data
	my $dataref = get_data($cgi);
	$$dataref{cookie} = $cookie_value;

	# Add visit entry to MySQL
	my $visitor_id = add_visitor_db($dbh, $dataref);
	add_visit_db($dbh, $dataref, $visitor_id);

	# Disconnect from database
	$dbh->disconnect();

}



#################### SUBROUTINES ####################

# return value of cookie, or undef if there is none
sub get_cookie {
	my ($cookie_name) = @_;
	my %cookies = CGI::Cookie->fetch();
	my $cookie = $cookies{$cookie_name};
	if ($cookie) {
		return $cookie->value();
	} else {
		return;
	}
}

# Set cookie to a random 96-bit value
sub set_cookie {
	
	my ($cookie_name, $domain) = @_;
	
	my $cookie_value = randchar("aA1", 16, '+', '-');
	my $cookie = CGI::Cookie->new(
			-name	=> $cookie_name,
			-value	=> $cookie_value,
			-expires => '+10y',
			-domain	=> '.' . $domain,
	);
	$cookie->bake();
	
	return $cookie_value;
	
}

# Pack up a %data hash with visit information.
sub get_data {
	
	my ($cgi) = @_;
	
	my %data;
	
	$data{unix_time} = time;
	$data{ip} = $cgi->remote_addr();
	$data{referrer} = $cgi->referer();
	$data{user_agent} = $cgi->user_agent();
	$data{page} = $ENV{HTTP_HOST} . $ENV{REQUEST_URI};
	
	return \%data;
}

# Adds visitor data to MySQL database (if it isn't in there already)
# Returns the visitor_id
sub add_visitor_db {
	
	my ($dbh, $dataref) = @_;
	
	my $ip = $$dataref{ip};
	my $user_agent = $$dataref{user_agent};
	my $cookie = $$dataref{cookie};
	
	
	# Check if visitor is already in database, return its visitor_id if so
	
	my $select_command = qq{
			SELECT visitor_id
			FROM visitors
			WHERE ip = ? AND user_agent = ? 
	};
	
	if ($cookie) {
		$select_command .= "AND cookie = ? ;";
	} else {
		$select_command .= "AND cookie IS NULL ;";
	}
	
	my $dsh = $dbh->prepare($select_command);
	if ($cookie) {
		$dsh->execute( $ip, $user_agent, $cookie );
	} else {
		$dsh->execute( $ip, $user_agent );
	}
	
	if (my $visitor_id = $dsh->fetchrow_array) {
		return $visitor_id;
	}
	
	
	# Insert new visitor into database
	
	my $label;
	my $is_me;
	if (is_it_me($dataref)) {
		$label = "me";
		$is_me = '';
	}
	
	my $insert_command = qq{
		INSERT INTO visitors (cookie, ip, user_agent, label, is_me)
		VALUES ( ?, ?, ?, ?, ? );
	};
	
	$dsh = $dbh->prepare($insert_command);
	$dsh->execute( $cookie, $ip, $user_agent, $label, $is_me );
	
	
	# Get visitor_id of new entry
	
	$dsh = $dbh->prepare($select_command);
	if ($cookie) {
		$dsh->execute( $ip, $user_agent, $cookie );
	} else {
		$dsh->execute( $ip, $user_agent );
	}
	
	my $visitor_id = $dsh->fetchrow_array;
	
	$dsh->finish();
	
	return $visitor_id;
}

# Add data on this particular visit to the database
# Splits into two main scenarios: referrer provided or not?
sub add_visit_db {
	
	my ($dbh, $dataref, $visitor_id) = @_;
	
	if ($$dataref{referrer}) {
	
		my $command = qq{
			INSERT INTO visits (visitor_id, unix_time, page, referrer)
			VALUES ( ?, ?, ?, ? );
		};
		
		my $dsh = $dbh->prepare($command);
		$dsh->execute(
				$visitor_id,
				$$dataref{unix_time},
				$$dataref{page},
				$$dataref{referrer},
		);
		
	} else {
	
		my $command = qq{
			INSERT INTO visits (visitor_id, unix_time, page)
			VALUES ( ?, ?, ? );
		};
		
		my $dsh = $dbh->prepare($command);
		$dsh->execute(
				$visitor_id,
				$$dataref{unix_time},
				$$dataref{page},
		);
	}
	
}