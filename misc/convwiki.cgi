#!/usr/bin/perl -w
#convwiki.cgi
#
# Quick tool for translating https wikipedia links into http ones

use strict;
use CGI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use Traffic;

# log the visit
add_visit_plain();

my $cgi = new CGI;

my $urls = $cgi->param('urls');

unless ($urls) {
	output($cgi, "No urls provided.<br>");
}

if ($urls =~
	s#s://secure\.wikimedia\.org/wikipedia/en/wiki/(\S*)#://en.wikipedia.org/wiki/$1#g) {
	$urls = HTML_encode($urls);
	output($cgi, $urls);
} else {
	output($cgi,
		"URLs did not match pattern.<br>\n" .
		"Input:<br>\n" . $urls
	);
}




sub output {
	
	my ($cgi, $output) = @_;
	
	print $cgi->header('text/html');
	print '<link rel="stylesheet" href="/css/style.css?v=2">', "\n";
	print $output;
	exit;
}

sub HTML_encode {
	my ($text) = @_;
	$text =~ s/</&lt;/g;
	$text =~ s/>/&gt;/g;
	$text =~ s/\n/<br>/g;
	return $text;
}