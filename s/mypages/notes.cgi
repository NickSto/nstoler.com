#!/usr/bin/perl -w
#notes.cgi
#
# Displays my customized page of notes from the notes entries stored in MySQL


########## MAIN BODY ##########

use strict;
use CGI;
use HTML::Template;
use DBI;
use Config::IniFiles;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;

# Constants
my $root = $ENV{'DOCUMENT_ROOT'};
my $TMPL_FILE = "notes.tmpl";
my $CONFIG_FILE = "$root/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $NAVBAR_FILE = "$root/navbar.d.html";

# Read in navbar HTML
open(my $navbar_fh, "<", $NAVBAR_FILE) or
	warn "Error: Cannot open navbar file $NAVBAR_FILE: $!";
my $navbar = join('', <$navbar_fh>);

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get notes from MySQL
my ($notes) = get_notes($dbh);

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
if (defined(@$notes)) {
	$tmpl->param( NOTES => $notes );
}

# Print HTML
print $cgi->header('text/html');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();



#################### SUBROUTINES ####################

# Gets the existing notes from the database
sub get_notes {
	
	my ($dbh) = @_;
	
	my $query = qq{
		SELECT note_id, content
		FROM notes
		ORDER BY note_id ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute();
	
	my $links;
	while ( my $row = $dsh->fetchrow_hashref ) {
		push(@$links, {
			NOTE_ID => $$row{note_id},
			CONTENT => NBSP(hyperlink(HTML_encode($$row{content}))),
		} );
	}
	
	$dsh->finish();
	
	return ($links);
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

# Automatically create hyperlinks when urls are detected
sub hyperlink {
	my ($text) = @_;
	unless ($text =~ m#&lt;a .*?href=".*?"&gt;#) {
		$text =~ s#(http(s?)://\S*\.\S*)(<br>)?#<a target="_blank" rel="nofollow" href="$1">$1</a>#g;
	}
	return $text;
}