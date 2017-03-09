#!/usr/bin/perl -w
#traffic-clean.cgi
# Cleanup the traffic database.
# 1. Mark visitors with the same cookie with the same label

use strict;
use Env;
use CGI;
use DBI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;

# Constants
my $CONFIG_FILE = "$ENV{'DOCUMENT_ROOT'}/protect/dbi_config.ini";
my $CONFIG_SECTION = "Tracker";
my $HTML_PRE = <<END;
<!doctype html>
<html>
  <head>
    <title>Traffic database cleaning</title>
    <link rel="stylesheet" id="nom" href="/nom.cgi">
  </head>
  <body>
END
my $HTML_POST = <<END;
    <p>Back to <a href='monitor.cgi'>traffic log</a>.</p>
  </body>
</html>
END

# Set up CGI and DBI objects 
my $cgi = new CGI;
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Debug DBI actions
# $dbh->trace($dbh->parse_trace_flags('SQL|1'));

# Do cleanup
my $count = fill_empty_labels($dbh);

# Disconnect from database
$dbh->disconnect();

# Print the HTML
print $cgi->header('text/html');
print $HTML_PRE;
print "    <p>Success! Updated $count visitors.</p>\n";
print $HTML_POST;




#################### SUBROUTINES ####################

# Loop through the rows once, from earliest to latest visit, building a hash
# mapping cookies to visitor data, and when we encounter a visitor with no
# label/is_me, we fill them in using the most recently observed visitor with
# that cookie.
sub fill_empty_labels {
	
	my ($dbh) = @_;
	
	my $query = qq{
		SELECT vtr.visitor_id, vt.unix_time, vtr.cookie, vtr.ip, vtr.label, vtr.is_me
		FROM visits vt
		JOIN visitors vtr ON vt.visitor_id = vtr.visitor_id
		ORDER BY vt.unix_time ASC;
	};
	
	my $dsh = $dbh->prepare($query);
	$dsh->execute();

	my %updated;
	my %visitors;
	my $count = 0;
	while ( my $row = $dsh->fetchrow_hashref ) {
		# last if ($count > 10);
		my $id = $$row{visitor_id};
		my $ip = $$row{ip};
		my $cookie = $$row{cookie};
		my $label = $$row{label};
		my $is_me = $$row{is_me};
		# cookie is NULL sometimes
		if (! defined($cookie)) {
			next;
		}

		# Catch visitors with NULL is_me or label values.
		if (! (defined $is_me && defined $label)) {
			if ($visitors{$cookie} && ! $updated{$id}) {
				my $visitor = $visitors{$cookie};
				# update_visitor will only copy the label if the IP's are the same.
				# So if the IP's are different and the is_me is already set, nothing
				# will be changed (so don't even call it).
				if ($ip eq $$visitor{ip} || ! defined $is_me) {
					if ($ENV{DEBUG}) {
						print "Matched labeled visitor:\n";
						print_user($$visitor{id});
					}
					if (update_visitor($dbh, $row, $visitor)) {
						$updated{$id} = 1;
						$count++;
					}
				}
			}
		# Otherwise, add the visitor info to the hash.
		# More recent entries will overwrite older ones for that cookie.
		} else {
			$visitors{$cookie} = {
				id => $id,
				ip => $ip,
				label => $label,
				is_me => $is_me,
			};
		}
	}
	
	$dsh->finish();
	return $count;
}


# Update the $src visitor with the $dest label and/or is_me values. 
# Notes:
#   Only writes to a field if it's NULL.
#   You can use a placeholder like "is_me = ?" even if $is_me is undef (NULL).
sub update_visitor {
	my ($dbh, $dest, $src) = @_;

	# Return variable. True if an update was made.
	my $updated = 0;

	if ($ENV{DEBUG}) {
		print "With unlabeled visitor:\n";
		print_user($$dest{visitor_id});
	}

	# Update the label (only if the ip is the same).
	if (! defined $$dest{label} && $$src{ip} eq $$dest{ip}) {
		$updated = 1;
		if ($ENV{DEBUG}) {
			print "Updated $$dest{visitor_id} with label \"$$src{label}\"\n";
		} else {
			my $query = qq{
				UPDATE visitors
				SET label = ?
				WHERE visitor_id = ?;
			};
			my $dsh = $dbh->prepare($query);
			$dsh->execute($$src{label}, $$dest{visitor_id});
		}
	}

	# Update the is_me.
	if (! defined $$dest{is_me}) {
		$updated = 1;
		if ($ENV{DEBUG}) {
			print "Updated $$dest{visitor_id} with is_me \"$$src{is_me}\"\n";
		} else {
			my $query = qq{
				UPDATE visitors
				SET is_me = ?
				WHERE visitor_id = ?;
			};
			my $dsh = $dbh->prepare($query);
			$dsh->execute($$src{is_me}, $$dest{visitor_id});
		}
	}

	if ($ENV{DEBUG}) {
		if (! $updated) {
			print "No updates made!\n";
		}
		print "\n";
	}
	return $updated;
}


# For debug printing
sub print_user {
	my ($id) = @_;

	my @properties = qw/ip is_me label cookie user_agent/;

	my $query = qq{
		SELECT ip, is_me, label, cookie, user_agent
		FROM visitors
		WHERE visitor_id = ?;
	};
	my $dsh = $dbh->prepare($query);
	$dsh->execute($id);
	my $row = $dsh->fetchrow_hashref;
	for my $property (@properties) {
		if (defined $$row{$property}) {
			$$row{$property} = '"'.$$row{$property}.'"';
		} else {
			$$row{$property} = "NULL";
		}
	}

	print "id: $id  cookie: $$row{cookie}  ip: $$row{ip}\t";
	print "label: $$row{label}\tis_me: $$row{is_me}\n";
	print "$$row{user_agent}\n";
}