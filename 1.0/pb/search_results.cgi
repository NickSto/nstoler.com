#!/usr/bin/perl -w
#search_results.cgi
=begin comment

Part of the Paralogy Browser application.

This script finds a user's search term in the product names of genes in the
MySQL database, then returns a page with the results. The results page contains
links that will bring up the similar genes page for any search result.

TODO:
	Allow someone to directly enter a gi number and go straight to the
		gene's page.

=end comment
=cut

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
my $TMPL_FILE = "search_results.tmpl";
my $CONFIG_FILE = "$root/protect/dbi_config.ini";
my $CONFIG_SECTION = "PBReader";
my $NAVBAR_FILE = "$root/navbar.d.html";

# Read in navbar HTML
open(my $navbar_fh, "<", $NAVBAR_FILE) or
	warn "Error: Cannot open navbar file $NAVBAR_FILE: $!";
my $navbar = join('', <$navbar_fh>);

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get query from POST
my $query = $cgi->url_param('query');
unless ($query) {
	$query = "no search terms entered!";
}

# Actual program logic (finding query)
my $results = get_matches($dbh, $query);
my $results = get_hits($dbh, $results);
my $matches = 0;
if (defined(@$results)) {
	$matches = scalar(@$results);
}

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
$tmpl->param( QUERY => HTML_encode($query) );
$tmpl->param( MATCHES => $matches );
if ($matches) {
	$tmpl->param( RESULTS => $results );
}

# Print HTML
print $cgi->header('text/html');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();





#################### SUBROUTINES ####################

# Finds genes in the database (the "sequences" table) with descriptions which
# contain the search query string.
sub get_matches {
	
	my ($dbh, $search_term) = @_;
	my $search_expression = "%$search_term%";
	
	my $query = qq{
		SELECT identifier, description
		FROM sequences
		WHERE description like ?
		ORDER BY description DESC ;
	};
	
	my $dsh = $dbh->prepare($query);
	   $dsh->execute($search_expression);
	
	my $results;
	while ( my $row = $dsh->fetchrow_hashref ) {
		push(@$results, {
			identifier => $$row{identifier},
			description => $$row{description}
			} );
	}
	
	$dsh->finish();
	
	return $results;
}

# Finds number of hits for each sequence returned in get_matches
sub get_hits {
	
	my ($dbh, $results) = @_;
	
	my $query = qq{
		SELECT COUNT(*)
		FROM hits
		WHERE query_id = ? ;
	};
	
	my $dsh = $dbh->prepare($query);
	for my $result (@$results) {
		$dsh->execute($$result{identifier});
		if (my $hits = $dsh->fetchrow_array) {
			$$result{hits} = $hits;
		} else {
			$$result{hits} = 0;
		}
	}
	
	return $results;
}

# Avoids simple HTML code injection.
# This is for strings that will be displayed as text on the page.
sub HTML_encode {
	my ($text) = @_;
	$text =~ s/</&lt;/g;
	$text =~ s/>/&gt;/g;
	return $text;
}