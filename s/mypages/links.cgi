#!/usr/bin/perl -w
#links.cgi
#
# Displays my customized page of links from the link entries stored in MySQL


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
my $TMPL_FILE = "links.tmpl";
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

# Get links from MySQL
my ($links) = get_links($dbh);

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
if (defined(@$links)) {
	$tmpl->param( LINKS => $links );
}

# Print HTML
print $cgi->header('text/html');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();





#################### SUBROUTINES ####################

# Gets the existing links from the database
sub get_links {
	
	my ($dbh) = @_;
	
	my $query = qq{
		SELECT link_id, link, linktext, comment
		FROM links
		ORDER BY link_id ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute();
	
	my $links;
	while ( my $row = $dsh->fetchrow_hashref ) {
		push(@$links, {
			LINK_ID => $$row{link_id},
			LINK => format_link($$row{link}, $$row{linktext}),
			COMMENT => $$row{comment}
		} );
	}
	
	$dsh->finish();
	
	return ($links);
}

# Format link into '<a href../a>' unless it's a line break
sub format_link {
	
	my ($link, $linktext) = @_;
	
	my $BREAK_WORD = 'BREAK';
	my $BREAK_TEXT = '=== BREAK ===';
	
	if ($link eq $BREAK_WORD) {
		return $BREAK_TEXT;
	} else {
		return '<a href="' . $link . '">' . $linktext . '</a>';
	}
}
