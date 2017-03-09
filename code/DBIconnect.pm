#!/usr/bin/perl -w
#DBIconnect.pm
=begin comment

Standard "connect to MySQL" subroutines.

I was using this in 90% of my CGI scripts.
Not sure why I didn't break it out before.

Usage:
Call DBI_connect and pass in the path to the configuration .ini file, as well
as the section in the config file to read for connection information.

=end comment
=cut

use strict;
use DBI;
use Config::IniFiles;

# Connects to a MySQL database. Takes the .ini config file as a parameter and
# returns an open database handle.
sub DBI_connect {
	
	my ($config_file, $config_section) = @_;
	
	my $config = get_config($config_file, $config_section);

	my $dsn = 'DBI:mysql:database=' . $$config{database} .
		';host=' . $$config{host};
	my $options = { RaiseError => 1, PrintError => 1 };

	return DBI->connect($dsn, $$config{user}, $$config{password}, $options);
	
}

# For connecting to MySQL database.
# Retrieves connection information from external .ini file and returns in a
# hash reference.
sub get_config {
	
	my ($config_file, $config_section) = @_;
	
	my $config = Config::IniFiles->new( -file => $config_file ) or
		die "failed to read INI file $config_file: $!";
	
	my %config;
	
	$config{user} = $config->val($config_section, 'user');
	$config{password} = $config->val($config_section, 'password');
	$config{host} = $config->val($config_section, 'host');
	$config{database} = $config->val($config_section, 'database');
	
	return \%config;
}

1;