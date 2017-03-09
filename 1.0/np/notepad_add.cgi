#!/usr/bin/perl -w
#notepad_add.cgi
=begin comment

For my Notepad web application.

This takes the text of a note submitted via HTML form and adds it to the
MySQL database under the appropriate page title.
First it cleans the text of special HTML characters and does other formatting
for HTML display.

=end comment
=cut

use strict;
use CGI qw(-utf8);
#use CGI;
use DBI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;
use Traffic;
use Encode;

binmode(STDOUT, ":utf8");
binmode(STDIN, ":utf8");

# Log the visit
add_visit_plain();

# Constants
my $CONFIG_FILE = "$ENV{'DOCUMENT_ROOT'}/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $MAIL_TO = 'nmapsy@gmail.com';
my $MAIL_FROM = 'notepad@'.$ENV{HTTP_HOST};

# Set up CGI and DBI objects 
my $cgi = new CGI;
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);
$dbh->{'mysql_enable_utf8'} = 1;

# Get the form info from the POST
#my $content = decode utf8=>param('content');
my $content = $cgi->param('content');
my $page = $cgi->param('page_name');
my $spambot = $cgi->param('site');
$page =~ s#^/##g;

if ($page eq "notepad") {
	send_mail($MAIL_TO, $MAIL_FROM,
		"WARNING: Someone added a post to Notepad's explanation page!",
		$cgi->remote_addr() . " added:\n" .
		substr($content, 0, 1024) . "\n");
}

# Add note to MySQL
if ($spambot) {
	my $subject = "SPAMBOT detected on $ENV{HTTP_HOST}!";
	my $message = "Spambot! " . $cgi->remote_addr() .
		": $ENV{HTTP_HOST}" . "$ENV{REQUEST_URI}\n" .
		"page: $page, hidden field entry: $spambot\n" .
		"submission: " . substr($content, 0, 1024) . "\n";
	print STDERR $message;
	send_mail($MAIL_TO, $MAIL_FROM, $subject, $message);
} else {
	add_note($dbh, $page, $content);
}

print $cgi->redirect('/' . $page . '#bottom');

# Disconnect from database
$dbh->disconnect();




#################### SUBROUTINES ####################

# Adds note to MySQL database
sub add_note {
	
	my ($dbh, $page, $content) = @_;
	
	my $command = qq{
		INSERT IGNORE INTO notepad (page, content)
		VALUES ( ?, ? );
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($page, $content);
	
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
