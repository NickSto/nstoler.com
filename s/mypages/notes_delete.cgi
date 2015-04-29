#!/usr/bin/perl -w
#notes_delete.cgi
=begin comment
Removes notes from the notes.cgi page via a web form and my MySQL database

Note: I encountered a problem in processing notes to be deleted. Here's what
	the issue was and how I solved it:
		Because I get checkbox status by checking the name of each checkbox,
	(e.g. "$cgi->param('note_6')"), I need to know how many boxes there are to
	check.
		The first thought would be to check every number until you stop getting
	a response. But there's two problems with that. First, the value of a
	checkbox that isn't checked is simply undef, so I can't tell the difference
	between an unchecked checkbox and one that doesn't exist. Also, the note_id
	numbers are sporadic and non-sequential.
		So an exhaustive search won't work. And there's no easy way I know of
	to get that information from the displayed page back to this script through
	the form. So instead I had to add a subroutine here that queries the
	database for the currently existing entries.
	

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
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;
use Passhash;
use Traffic;
	
# Log the visit
add_visit_plain();

# Constants
my $root = $ENV{'DOCUMENT_ROOT'};
my $TMPL_FILE = "notes.tmpl";
my $CONFIG_FILE = "$root/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $HASH_FILE = "$root/protect/auth.ini";

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

# Get list of existing notes from database
my @note_ids = get_current_notes($dbh);

# Go through checkboxes and delete selected links
for my $note_id (@note_ids) {
	my $yes_delete = $cgi->param("note_$note_id");
	if ($yes_delete) {
		delete_note($dbh, $note_id);
	}
}

exeunt($cgi, $dbh);

sub exeunt {
	
	my ($cgi, $dbh) = @_;
	
	print $cgi->redirect('notes.cgi');
	
	# Disconnect from database
	$dbh->disconnect();
	
	exit;
}



#################### SUBROUTINES ####################

# Get the list of existing links in the database
sub get_current_notes {
	
	my ($dbh) = @_;
	
	my $query = qq{
		SELECT note_id
		FROM notes ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute();
	
	my @note_ids;
	while ( my @row = $dsh->fetchrow_array ) {
		push(@note_ids, $row[0]);
	}
	
	return @note_ids;
	
}

# Finds genes in the database (the "sequences" table) with descriptions which
# contain the search query string.
sub delete_note {
	
	my ($dbh, $note_id) = @_;
	
	my $command = qq{
		DELETE FROM notes
		WHERE note_id = ? ;
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($note_id);
	
	$dsh->finish();
}