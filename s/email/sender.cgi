#!/usr/bin/perl -w
#email.cgi
# Making a generic email sender

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use Config::IniFiles;
use lib '/home/public/code';
use Passhash;
use Traffic;
	
# Log the visit
add_visit_plain();

# Constants
my $HASH_FILE = "/home/public/protect/auth.ini";

my $error = 0;

# Set up CGI object
my $cgi = new CGI;

# Get query from POST
my $to = $cgi->param('to');
my $from = $cgi->param('from');
my $subject = $cgi->param('subject');
my $body = $cgi->param('body');
my $auth = $cgi->param('auth');
my $spambot = $cgi->param('url');

# Check authentication
my $hash_db = Config::IniFiles->new( -file => $HASH_FILE );
unless ($hash_db) {
	print STDERR "failed to read INI file $HASH_FILE: $!";
	$error = "true";
}
my $hash1 = $hash_db->val('SVH', 'main');
my $hash2 = $hash_db->val('SVH', 'shared');
my $salt = $hash_db->val('SVH', 'salt');
my $hashed_pass = salted_vary_hash($auth, $salt);
unless ($hashed_pass eq $hash1 or $hashed_pass eq $hash2) {
	print STDERR "incorrect password\n";
	exeunt($cgi, 'authfail.html');
}

# check spambot detection field
if ($spambot) {
	print STDERR "SPAMBOT!";
	exeunt($cgi, 'form.html');
}

unless (send_mail($to, $from, $subject, $body)) {
	$error = "true";
}

if ($error) {
	exeunt($cgi, 'failure.html');
} else {
	exeunt($cgi, 'success.html');
}

sub exeunt {
	
	my ($cgi, $page) = @_;
	
	# Redirect to the appropriate page
	print $cgi->redirect($page);
	
	exit;
}


#################### SUBROUTINES ####################

# Uses sendmail to send the email.
# Returns false on failure, true on (apparent) success.
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