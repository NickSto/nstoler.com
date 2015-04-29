#!/usr/bin/perl -w
#contact_send.cgi
# Contact form email sender

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use Traffic;
	
# Log the visit
add_visit_plain();

# Constants
my $TO = 'nmapsy@gmail.com';
my $FROM_PREFIX = 'contact';

# Get the domain
my $domain = "$ENV{'HTTP_HOST'}";
if ($ENV{HTTP_HOST} =~ m/([^.]+\.[^.]+)$/) {
	$domain = $1;
}

# Global variables
my $from = $FROM_PREFIX . '@' . $domain;
my $error = 0;

# Set up CGI object
my $cgi = new CGI;

# Get query from POST
my $subject = $cgi->param('subject');
my $body = $cgi->param('body');
my $spambot = $cgi->param('url');

# check spambot detection field
if ($spambot) {
	print STDERR "SPAMBOT!";
	exeunt($cgi, 'form.html');
}

# Send the email
unless (send_mail($TO, $from, $subject, $body)) {
	$error = "true";
}

# Redirect to a success or failure page
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