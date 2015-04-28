#!/usr/bin/perl -w
#notepad_delete.cgi
=begin comment

For my Notepad web application.

Deletes notes selected via a web form (and submitted via HTTP POST) from the
MySQL database.

=end comment
=cut

use strict;
use CGI;
use DBI;
use lib '/home/public/code';
use DBIconnect;
use Traffic;

# Log the visit
add_visit_plain();

# Constants
my $CONFIG_FILE = "/home/public/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $MAIL_TO = 'nmapsy@gmail.com';
my $MAIL_FROM = 'notepad@'.$ENV{HTTP_HOST};

# Set up CGI and DBI objects 
my $cgi = new CGI;
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get the form info from the POST
my $page = $cgi->param('page_name');
my $spambot = $cgi->param('site');

# Get list of existing notes from database
my @note_ids = get_current_notes($dbh, $page);

my @deleted = ();

# Go through checkboxes and delete selected links
if ($spambot) {
        my $subject = "SPAMBOT detected on $ENV{HTTP_HOST}!";
        my $message = "Spambot! " . $cgi->remote_addr() .
                ": $ENV{HTTP_HOST}" . "$ENV{REQUEST_URI}\n" .
                "page: $page, hidden field entry: $spambot\n";
        print STDERR $message;
        send_mail($MAIL_TO, $MAIL_FROM, $subject, $message);
} else {
	for my $note_id (@note_ids) {
		my $yes_delete = $cgi->param("note_$note_id");
		if ($yes_delete) {
			delete_note($dbh, $note_id);
			push(@deleted, $note_id);
		}
	}
}

# Send out a warning email if someone messed with the demo page
if ($page eq "notepad") {
        send_mail($MAIL_TO, $MAIL_FROM,
                "WARNING: Someone deleted a post from Notepad's explanation page!",
                $cgi->remote_addr() . " deleted note_id(s) @deleted\n" .
		"(The ones you wanted to keep are 1801, 1802, and 1803.)\n");
}

print $cgi->redirect('/' . $page . '#bottom');

# Disconnect from database
$dbh->disconnect();




#################### SUBROUTINES ####################

# Get the list of existing notes on this page from the database
sub get_current_notes {
	
	my ($dbh, $page) = @_;
	
	my $query = qq{
		SELECT note_id
		FROM notepad
		WHERE page = ? ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute($page);
	
	my @note_ids;
	while ( my @row = $dsh->fetchrow_array ) {
		push(@note_ids, $row[0]);
	}
	
	return @note_ids;
	
}

# Deletes notes from the database that match the specified note_id
sub delete_note {
	
	my ($dbh, $note_id) = @_;
	
	my $command = qq{
		DELETE FROM notepad
		WHERE note_id = ? ;
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($note_id);
	
	$dsh->finish();
}

# (this is copied from /s/email/sender.cgi)
sub send_mail {

        my ($to, $from, $subject, $body) = @_;

        my $message = "From: $from\n" .
                "To: $to\n" .
                "Subject: $subject\n\n" .
                "$body\n";

        unless (open(MAIL, "| sendmail -oi -t")) {
                print STDERR "could not open pipe to sendmail";
                return 0;
        }

        print MAIL $message;
        close(MAIL);
        return "success";
}

