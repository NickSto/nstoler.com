#!/usr/bin/perl -w
#search_genes.cgi
=begin comment

Part of the Paralogy Browser application.

This script takes a gene identifier in the URL query string as input
(normally via a GET request but also directly, allowing bookmarks).
It then returns a page showing all the similar sequences in the same genome,
identified by a pre-run multiway BLAST search.

=end comment
=cut

########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use HTML::Template;
use DBI;
use Config::IniFiles;
use lib '/home/public/code';
use DBIconnect;

# Constants
my $HTML_TMPL = "similarities.tmpl";
my $CONFIG_FILE = "/home/public/protect/dbi_config.ini";
my $CONFIG_SECTION = "PBReader";
my $NAVBAR_FILE = "/home/public/navbar.d.html";

# Read in navbar HTML
open(my $navbar_fh, "<", $NAVBAR_FILE) or
	warn "Error: Cannot open navbar file $NAVBAR_FILE: $!";
my $navbar = join('', <$navbar_fh>);

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $HTML_TMPL);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get query from POST
my $queryID = $cgi->url_param('identifier');

# Actual program logic (getting hits information)
my $qDescription = get_description($dbh, $queryID);
my $hits = get_hits($dbh, $queryID);
my $numHits = 0;
if (defined(@$hits)) {
	$numHits = scalar(@$hits);
}

# Set CGI template variables
$tmpl->param( NAVBAR => $navbar );
$tmpl->param( Q_DESCRIPTION => $qDescription );
$tmpl->param( QUERY_ID => $queryID );
$tmpl->param( NUM_HITS => $numHits );
$tmpl->param( HITS => $hits );

# Print HTML
print $cgi->header('text/html');
print $tmpl->output;

# Disconnect from database
$dbh->disconnect();



#################### SUBROUTINES ####################

# Fetch the description text for the gene of interest from the database
sub get_description {
	
	my ($dbh, $identifier) = @_;
	
	my $query = qq{
		SELECT description
		FROM sequences
		WHERE identifier = ? ;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute($identifier);
	
	my @row = $dsh->fetchrow_array;
	my ($description) = @row;
	
	$dsh->finish();
	
	return $description;
}

# Gets the information on the sequences similar to the gene of interest from
# the database. It creates a hash of information for each "hit" and adds its
# reference to an array. Then it returns a reference to that array, ready to
# pass to the HTML template.
sub get_hits {
	
	my ($dbh, $queryID) = @_;
	
	my $query = qq{
		SELECT h.subject_id, h.identity, h.e_value, h.bit_score, h.align_length, s.description
		FROM hits h
		JOIN sequences s ON h.subject_id = s.identifier
		WHERE h.query_id = ? ;
	};
	
	my $dsh = $dbh->prepare($query);
	   $dsh->execute($queryID);
	
	my $hits;
	while ( my $row = $dsh->fetchrow_hashref ) {
		push(@$hits, {
			SUBJECT_ID => $$row{subject_id},
			S_DESCRIPTION => $$row{description},
			IDENTITY => $$row{identity},
			E_VALUE => $$row{e_value},
			BIT_SCORE => $$row{bit_score},
			ALIGN_LENGTH => $$row{align_length},
			BAR_WIDTH => get_width($$row{e_value})
		} );
	}
	
	$dsh->finish();
	
	return $hits;
}

# Converts an E-value into a pixel size for the E-value meter displays.
# It returns a meter bar width proportional to the log of the E-value
# (technically proportional to the negation of its natural log).
# 
# If the E-value is 0, then instead I set it to 1e-180, the smallest E-value
# returned by blastall.
# It's imprecise, but the bars are merely a visual aid.
sub get_width {
	
	my ($eValue) = @_;
	my $SCALE = 1.5;
	my $MIN = 1e-180;
	
	if ($eValue == 0) {
		$eValue = $MIN;
	}
	
	return int(-1 * $SCALE * log($eValue));
	
}