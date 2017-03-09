#!/usr/bin/perl -w
#urlconv.cgi
=begin comment

Quick tool for replacing percent-encoded characters in a string with their
equivalent ASCII characters.

=end comment
=cut

use strict;
use CGI;

my %CHARS = (		'%20' => ' ',	'%21' => '!',	'%22' => '"',
	'%23' => '#',	'%24' => '$',	'%25' => '%',	'%26' => '&',
	'%27' => "'",	'%28' => '(',	'%29' => ')',	'%2A' => '*',
	'%2B' => '+',	'%2C' => ',',	'%2D' => '-',	'%2E' => '.',
	'%2F' => '/',	'%3A' => ':',	'%3B' => ';',	'%3C' => '<',
	'%3D' => '=',	'%3E' => '>',	'%3F' => '?',	'%40' => '@',
	'%5B' => '[',	'%5C' => '\\',	'%5D' => ']',	'%5E' => '^',
	'%5F' => '_',	'%60' => '`',	'%7B' => '{',	'%7C' => '|',
	'%7D' => '}',	'%7E' => '~');

my $cgi = new CGI;

my $urls = $cgi->param('urls');

unless ($urls) {
	output($cgi, "No urls provided.<br>");
	exit;
}

for my $encoded (keys %CHARS) {
	$urls =~ s/$encoded/$CHARS{$encoded}/g;
}
$urls =~ s/\+/ /g;

$urls = HTML_encode($urls);
output($cgi, $urls);


########## SUBROUTINES ##########

# Print html out
sub output {
	
	my ($cgi, $output) = @_;
	
	print $cgi->header('text/html');
	print '<link rel="stylesheet" href="/css/style.css?v=2">', "\n";
	print $output;
	exit;
}

# Protect from script and HTML injection
sub HTML_encode {
	my ($text) = @_;
	$text =~ s/</&lt;/g;
	$text =~ s/>/&gt;/g;
	$text =~ s/\n/<br>/g;
	return $text;
}
