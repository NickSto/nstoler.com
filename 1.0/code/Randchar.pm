#!/usr/bin/perl -w
#randchar.pm
#
#Why is this not built into Perl?
use strict;

# Returns a random lowercase character from 'a' to 'z', or if a number is given
# as a parameter, it will return a string of that many characters.
sub randalpha {
	my ($length) = @_;
	
	unless ($length) {
		$length = 1;
	}
	
	return randchar("a", $length);
}

# Returns a random digit from 0 to 9, or if a number is given
# as a parameter, it will return a string of that many digits.
sub randdigit {
	my ($length) = @_;
	
	unless ($length) {
		$length = 1;
	}
	
	return randchar("1", $length);
}

# Returns a random symbol character from the set of printable ASCII, or if a
# number is given as a parameter, it will return a string of that many symbols.
sub randsymbol {
	my ($length) = @_;
	
	unless ($length) {
		$length = 1;
	}
	
	return randchar("!", $length);
}

# Returns a string containing random characters. If no parameters are supplied,
# it will return a single character from the set of all printable ASCII.
#
# Takes a string input to specify the type of characters to use: "aA1!"
# specifies lowercase alpha, uppercase alpha, digits, and all ASCII symbols.
# The string can contain any subset in any order to specify a different
# character set, e.g. "1a" for only digits and lowercase alpha.
#
# After the type string is an optional parameter to specify how many characters
# to return in the return string. This should be a number.
#
# After the number of characters parameter, you can optionally include a list
# of specific characters to include in addition to the types specified in the
# type string. So the full parameter list starts with the type string, then
# the number of characters, then a list of additional characters to include.
sub randchar {
	my ($type, $length, @extra) = @_;
	
	# default number of characters: 1
	unless (defined($length)) {
		$length = 1;
	}
	
	# build character set
	my @chars;
	if ($type) {
		if ($type =~ /a/) {
			push(@chars, ('a'..'z'));
		}
		if ($type =~ /A/) {
			push(@chars, ('A'..'Z'));
		}
		if ($type =~ /1/) {
			push(@chars, ('0'..'9'));
		}
		if ($type =~ /!/) {
			push(@chars, ('!','"','#','$','%','&','\'','(',')','*','+',
				',','-','.','/',':',';','<','=','>','?','@','[','\\',
				']','^','_','`','{','|','}','~'));
		}
		if (@extra) {
			push(@chars, @extra);
		}
	} else {
		push(@chars, ('a'..'z','A'..'Z','0'..'9','!','"','#','$','%','&',
			'\'','(',')','*','+',',','-','.','/',':',';','<','=','>','?',
			'@','[','\\',']','^','_','`','{','|','}','~'));
	}
	
	# build the string
	my $string = "";
	while (length($string) < $length) {
		my $index = int(rand(@chars));
		$string .= $chars[$index];
	}
	
	return $string;
}


"true";