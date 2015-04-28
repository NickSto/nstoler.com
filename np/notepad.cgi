#!/usr/bin/perl -w
#notepad.cgi
=begin comment

For my Notepad web application.

Displays a page of notes held in the MySQL database, determining which page to
display by a parameter in the url query string (like a GET request).

=end comment
=cut

use strict;
use CGI;
use HTML::Template;
use DBI;
use lib '/home/public/code';
use DBIconnect;

# Constants
my $TMPL_FILE = "notepad.tmpl";
my $CONFIG_FILE = "/home/public/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $NAVBAR_FILE = "/home/public/navbar.d.html";
my $RANDOM_PAGE = "/home/public/np/random.cgi";

# Read in navbar HTML
open(my $navbar_fh, "<", $NAVBAR_FILE) or
	warn "Error: Cannot open navbar file $NAVBAR_FILE: $!";
my $navbar = join('', <$navbar_fh>);

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);
$dbh->{'mysql_enable_utf8'} = 1;

# Get the page name from the GET
my $page = $cgi->url_param('p');

# Get random page if none supplied
unless ($page) {
	exec $RANDOM_PAGE;
}

# Get notes from MySQL
my ($notes) = get_notes($dbh, $page);

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
$tmpl->param( PAGE => $page );
if (defined(@$notes)) {
	$tmpl->param( NOTES => $notes );
}

# Print the HTML
#print $cgi->header('text/html');
print $cgi->header(-type=>'text/html', -charset=>'utf-8');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();




#################### SUBROUTINES ####################

# Finds notes for the selected page
sub get_notes {
	
	my ($dbh, $page) = @_;
	
	my $query = qq{
		SELECT note_id, content
		FROM notepad
		WHERE page = ?
		ORDER BY note_id ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute($page);
	
	my $notes;
	while ( my $row = $dsh->fetchrow_hashref ) {
		my $content = NBSP(hyperlink(HTML_encode($$row{content})));
		push(@$notes, {
			NOTE_ID => $$row{note_id},
			CONTENT => $content,
			BOTTOM => '',
		} );
	}
	# add "bottom" anchor to last note
	if ($notes) {
		@$notes[$#$notes]->{BOTTOM} = 'id="bottom" ';
	}

	
	# sort { $$a{NOTE_ID} <=> $$b{NOTE_ID} } @$notes;
	
	$dsh->finish();
	
	return ($notes);
}

# Avoids simple HTML code injection.
# This is for strings that will be displayed as text on the page.
# Currently also inserts <br> tags at newlines, though I intend to replace this
# functionality with more proper HTML.
sub HTML_encode {
	my ($text) = @_;
	$text =~ s/&/&amp;/g;
	$text =~ s/</&lt;/g;
	$text =~ s/>/&gt;/g;
	$text =~ s/\n/<br>/g;
	return $text;
}

# Changes some spaces to NBSP to get around HTML's tendency to not count
# spaces in certain places (like at the beginning of a line or after another
# space). I don't want to replace all spaces because then I get completely
# non-breaking lines.
# It's a bit hacky at the moment. Not sure what the best way to do this is.
sub NBSP {
	
	my ($text) = @_;
	
	$text =~ s/^ /&nbsp;/g;
	$text =~ s/\n /\n&nbsp;/g;
	
	# Perform substitution until it no longer matches.
	# Can't be global because I need it to walk along the string.
	while ($text =~ s/  /&nbsp; /) { 0 }
	
	return $text;
}

sub hyperlink {
	my ($text) = @_;
	unless ($text =~ m#&lt;a .*?href=".*?"&gt;#) {
		$text =~ s#(http(s?)://\S*\.\S*)(<br>)?#<a target="_blank" rel="nofollow" href="$1">$1</a>#g;
	}
	return $text;
}
