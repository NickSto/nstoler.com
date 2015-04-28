#!/usr/bin/perl -w
#links_add.cgi
#
# Adds a link from the links.cgi page via a web form and my MySQL database


########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use HTML::Template;
use DBI;
use Config::IniFiles;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;
use Passhash;
use Traffic;
	
# Log the visit
#add_visit_plain();

# Constants
my $root = $ENV{'DOCUMENT_ROOT'};
my $TMPL_FILE = "links.tmpl";
my $CONFIG_FILE = "$root/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $HASH_FILE = "$root/protect/auth.ini";

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get query from POST
my $link = $cgi->param('url');
my $linktext = $cgi->param('title');
my $comment = $cgi->param('comment');
my $auth = $cgi->param('auth');

# Check authentication
my $hash_db = Config::IniFiles->new( -file => $HASH_FILE ) or
		die "failed to read INI file $HASH_FILE: $!";
my $hash = $hash_db->val('SVH', 'main');
my $salt = $hash_db->val('SVH', 'salt');
unless (salted_vary_hash($auth, $salt) eq $hash) {
	print STDERR "incorrect password\n";
	exeunt($cgi, $dbh);
}

# Clean inputs of special HTML characters
$link = URL_encode($link);
$linktext = HTML_encode($linktext);
$comment = HTML_encode($comment);

# Add link to MySQL
add_link($dbh, $link, $linktext, $comment);

exeunt($cgi, $dbh);


sub exeunt {
	
	my ($cgi, $dbh) = @_;
	
	print $cgi->redirect('links.cgi');
	
	# Disconnect from database
	$dbh->disconnect();
	
	exit;
}


#################### SUBROUTINES ####################

# Avoids simple HTML code injection.
# This is for strings that will be displayed as text on the page.
sub HTML_encode {
	my ($text) = @_;
	$text =~ s/</&lt;/g;
	$text =~ s/>/&gt;/g;
	return $text;
}

# Avoids other HTML code injections.
# This is for strings that will be part of a URL, like in the href attribute
# of a link.
sub URL_encode {
	my ($text) = @_;
	$text =~ s/</%3C/g;
	$text =~ s/>/%3E/g;
	$text =~ s/"/%22/g;
	$text =~ s/'/%27/g;
	return $text;
}

# Adds the link to the database
sub add_link {
	
	my ($dbh, $link, $linktext, $comment) = @_;
	
	my $command = qq{
		INSERT IGNORE INTO links (link, linktext, comment)
		VALUES ( ?, ?, ? );
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($link, $linktext, $comment);
	
	$dsh->finish();
}