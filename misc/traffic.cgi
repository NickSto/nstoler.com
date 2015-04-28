#!/usr/bin/perl -w
#traffic.cgi
=begin comment

Web interface for my traffic monitoring system.

This displays information about recent visits.

Todo:
	Work on the cases where it's the first and last pages

=end comment
=cut

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use HTML::Template;
use DBI;
use lib '/home/public/code';
use DBIconnect;
use Traffic;
use Auth;

# Constants
my $TMPL_FILE = "traffic.tmpl";
my $CONFIG_FILE = "/home/public/protect/dbi_config.ini";
my $CONFIG_SECTION = "Tracker";
my $NAVBAR_FILE = "/home/public/navbar.d.html";
my $NUM_PER_PAGE = 100;

# Read in navbar HTML
open(my $navbar_fh, "<", $NAVBAR_FILE) or
	warn "Error: Cannot open navbar file $NAVBAR_FILE: $!";
my $navbar = join('', <$navbar_fh>);

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# If cookie is not authorized, print error and exit
if (! admin_cookie()) {
	print $cgi->header('text/html');
	print "Error: You are not yet authorized for this content.\n";
	# Disconnect from database
	$dbh->disconnect();
	exit(0);
}

# Get query string options
my $include_me = ($cgi->url_param('me') eq "include");
my $page = $cgi->url_param('p');
unless ($page) {
	$page = 1;
}

# Get recent visits from MySQL
my ($visits) = get_visits($dbh, $page, $include_me);

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
if ($page > 1) {
	$tmpl->param( PREV => $page - 1 );
}
$tmpl->param( START => ($page - 1) * $NUM_PER_PAGE + 1);
if (defined(@$visits)) {
	$tmpl->param( END => (($page - 1) * $NUM_PER_PAGE) + @$visits );
	if (@$visits == $NUM_PER_PAGE) {
		$tmpl->param( NEXT => $page + 1 );
	}
	$tmpl->param( VISITS => $visits );
}

# Print the HTML
print $cgi->header('text/html');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();




#################### SUBROUTINES ####################

# Gets most recent visits from traffic database
sub get_visits {
	
	my ($dbh, $page, $include_me) = @_;
	
	my $NUM_PER_PAGE = 100;
	
	my $end = $page * $NUM_PER_PAGE;
	my $start = $end - $NUM_PER_PAGE + 1;
	
	my $query;
	if ($include_me) {
		$query = qq{
			SELECT vtr.ip, vt.page, vtr.cookie, vt.referrer, vt.unix_time, vtr.user_agent, vtr.label
			FROM visits vt
			JOIN visitors vtr ON vt.visitor_id = vtr.visitor_id
			ORDER BY vt.visit_id DESC
			LIMIT ? ;
		};
	} else {
		$query = qq{
			SELECT vtr.ip, vt.page, vtr.cookie, vt.referrer, vt.unix_time, vtr.user_agent, vtr.label
			FROM visits vt
			JOIN visitors vtr ON vt.visitor_id = vtr.visitor_id
			WHERE vtr.is_me IS NULL
			ORDER BY vt.visit_id DESC
			LIMIT ? ;
		};
	}
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute($end);
	
	my $counts = 0;
	my $visits;
	while ( my $row = $dsh->fetchrow_hashref ) {
		# for pagination: skip results below the requested page
		$counts++;
		unless ($counts >= $start) { next; }
		
		my $time = localtime($$row{unix_time});
		push(@$visits, {
			IP => $$row{ip},
			PAGE => $$row{page},
			COOKIE => $$row{cookie},
			REFERRER => $$row{referrer},
			TIME => $time,
			USER_AGENT => $$row{user_agent},
			LABEL => $$row{label}
		} );
	}
	
	$dsh->finish();
	
	return ($visits);
}
