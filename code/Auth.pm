#!/usr/bin/perl -w
#Auth.pm
=begin comment

Check whether cookie is in admin list.

=end comment
=cut

use strict;
use Config::IniFiles;
use CGI::Cookie;

# Check that the user has an authorized cookie
sub admin_cookie {
	my $COOKIE_NAME = "visitors_v1";
	my $AUTH_FILE = "$ENV{'DOCUMENT_ROOT'}/protect/auth.ini";
	
	my $user_cookie = get_cookie($COOKIE_NAME);
	my $auth_cookies = get_config_value($AUTH_FILE, 'Traffic', 'cookies');
	my $authorized = 0;
	for my $auth_cookie (split(',', $auth_cookies)) {
	  if ($auth_cookie eq $user_cookie) {
	    $authorized = 'true';
	  }
	}
	return $authorized;
	
}

sub get_cookie {
	my ($cookie_name) = @_;
	my %cookies = CGI::Cookie->fetch();
	my $cookie = $cookies{$cookie_name};
	if ($cookie) {
		return $cookie->value();
	} else {
		return;
	}
}

# Retrieve a single value from a config file.
# Inefficient for repeated queries, since it opens the file anew each time.
sub get_config_value {
	
	my ($config_file, $config_section, $config_key) = @_;
	
	my $config = Config::IniFiles->new( -file => $config_file ) or
		die "failed to read INI file $config_file: $!";
	
	return $config->val($config_section, $config_key);
}

1;