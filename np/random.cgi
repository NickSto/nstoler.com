#!/usr/bin/perl -w
#random.cgi
=begin comment

For my Notepad web application.

Redirects the user to a random Notepad page.

=end comment
=cut

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use lib '/home/public/code';
use Randchar;
use Traffic;

# Log the visit
add_visit_plain();

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;

# Get random page name
my $page = randalpha(5); 

# Print the HTML
print $cgi->redirect('/' . $page);