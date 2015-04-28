#!/usr/bin/perl -w
#links_delete.cgi
=begin comment
Removes links from the links.cgi page via a web form and my MySQL database

Note: I encountered a problem in processing links to be deleted. Here's what
	the issue was and how I solved it:
		Because I get checkbox status by checking the name of each checkbox,
	(e.g. "$cgi->param('link_6')"), I need to know how many boxes there are to
	check.
		The first thought would be to check every number until you stop getting
	a response. But there's two problems with that. First, the value of a
	checkbox that isn't checked is simply undef, so I can't tell the difference
	between an unchecked checkbox and one that doesn't exist. Also, the link_id
	numbers are sporadic and non-sequential.
		So an exhaustive search won't work. And there's no easy way I know of
	to get that information from the displayed page back to this script through
	the form. So instead I had to add a subroutine here that queries the
	database for the currently existing entries.*
		*First I used a kludge where I inserted an invisible text box into the
	form and filled it with the link_ids. But that stopped working for an
	unknown reason so I had to do it the "right" way.
	

=end comment
=cut

########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use HTML::Template;
use DBI;
use Config::IniFiles;
use lib '/home/public/code';
use DBIconnect;
use Passhash;
use Traffic;
	
# Log the visit
add_visit_plain();

# Constants
my $TMPL_FILE = "links.tmpl";
my $CONFIG_FILE = "/home/public/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $HASH_FILE = "/home/public/protect/auth.ini";

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Check authentication from POST
my $hash_db = Config::IniFiles->new( -file => $HASH_FILE ) or
		die "failed to read INI file $HASH_FILE: $!";
my $hash = $hash_db->val('SVH', 'main');
my $salt = $hash_db->val('SVH', 'salt');
my $auth = $cgi->param('auth');
unless (salted_vary_hash($auth, $salt) eq $hash) {
	print STDERR "incorrect password\n";
	exeunt($cgi, $dbh);
}

# Get list of existing links from database
my @link_ids = get_current_links($dbh);

# Go through checkboxes and delete selected links
for my $link_id (@link_ids) {
	my $yes_delete = $cgi->param("link_$link_id");
	if ($yes_delete) {
		delete_link($dbh, $link_id);
	}
}

exeunt($cgi, $dbh);

sub exeunt {
	
	my ($cgi, $dbh) = @_;
	
	print $cgi->redirect('links.cgi');
	
	# Disconnect from database
	$dbh->disconnect();
	
	exit;
}



#################### SUBROUTINES ####################

# Get the list of existing links in the database
sub get_current_links {
	
	my ($dbh) = @_;
	
	my $query = qq{
		SELECT link_id
		FROM links ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute();
	
	my @link_ids;
	while ( my @row = $dsh->fetchrow_array ) {
		push(@link_ids, $row[0]);
	}
	
	return @link_ids;
	
}

# Deletes the links from the database
sub delete_link {
	
	my ($dbh, $link_id) = @_;
	
	my $command = qq{
		DELETE FROM links
		WHERE link_id = ? ;
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($link_id);
	
	$dsh->finish();
}
