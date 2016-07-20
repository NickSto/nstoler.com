#!/usr/bin/perl -w
#random.cgi
=begin comment

For my Notepad web application.

Redirects the user to a random Notepad page.

=end comment
=cut

use strict;
use CGI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
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