#!/usr/bin/env perl
# run.pl
# interface wrapper for word checking 
# alex lustenberg, 2011

use strict;
use warnings;

use Algorithm::Permute;
use Carp;
use Data::Dumper;
use FileHandle;
use IPC::Open2;
use Getopt::Long;
use Time::HiRes qw(gettimeofday tv_interval);

local $| = 1; # flush output

my $init = [ gettimeofday() ];
my $runtime = "./trie2-run";

GetOptions("r|runtime=s" => \$runtime, );

my $trie = open2(*c_out, *c_in, $runtime) or croak "Cannot open subprocess : $!";
# snarf the startup messages
while(my $buff = <c_out>){
	chomp($buff);
	last if ($buff =~ /ready/);
	printf "|%s\n", $buff;
}
printf "ready for input, %.3fs init\n", tv_interval( $init );

my %letterValues = (
	'B' => 3, 
	'C' => 3, 
	'D' => 2, 
	'F' => 3, 
	'F' => 4, 
	'G' => 2, 
	'H' => 4, 
	'J' => 8,
	'K' =>.2,
	'M' => 3, 
	'Q' => 10,
	'V' => 4, 
	'W' => 4, 
	'X' => 8,
	'Y' => 4, 
	'Z' => 10,
);

sub valueWord { 
	my ($word) = @_;
	my $value = 0;
	foreach my $letter ( split(//, $word) ) { 
		$value += $letterValues{ uc $letter } || 1;
	}
	return $value;
}

#sub iterWildcards { 
#	my ($word) = @_;
#	
#	if($word =~ /^(.*)_(.*)$/){ # wildcard handler. ugh.
#		my $pre = $1 || "";
#		my $post = $2 || "";
#
#		foreach my $l ('A'..'Z'){ 
#			iterWildcards(sprintf "%s%s%s", $pre, $l, $post);
#		}
#	} else { 
#		printf STDERR "querying %s\n", $word;
#		printf c_in "%s\n", $word;
#	}
#}

	
sub checkWord { 
	my ($word) = @_;

	my %words;
	## iterWildcards($word);
	printf c_in "%.8s\n", $word;
	printf c_in "done\n";

	while(my $result = <c_out>){
		chomp($result);
		last if($result =~ m/done/);
		if($result =~ /^[A-Z]+$/){ 
			$words{ $result }  = valueWord($result);
		} else { 
			printf STDERR "%s\n", $result;
		} 
	}
	return \%words;
}

sub checkHand { 
	my ($hand) = @_;
	my %results = ();
	my $per = new Algorithm::Permute([ split(//, $hand) ]);

	while(my @word = $per -> next) { 
		my $matching = checkWord(join("", @word));
		foreach my $match( keys %{ $matching} ) { 
			$results{ $match } = $matching -> { $match } ;
		}
	}
	printf c_in "flush\n"; # flush causes the 'already matched' words to be reset
	<c_out>; # slurp the flush return

	return \%results;
}

while(1){ 
	printf "input hand? \n";
	
	my $hand = <STDIN>;
	last if ( not defined $hand );
	$hand = uc $hand;

	chomp($hand);
	
	my $start = [ gettimeofday() ];	

	my $results = checkHand($hand);
	my $total = 0.0;

	
	my $count = scalar( keys %{ $results } );
	printf "%d words found, %.3fs\n\n", 
		$count,
		tv_interval($start);

	if(scalar keys %{ $results }) { 
		printf "results :";
		my $lv = "";
		foreach my $result ( 
			sort { 
				$a -> [1] <=> $b -> [1] || 
				length($a -> [0]) <=> length($b -> [0]) ||
				$a -> [0] cmp $b -> [0]
			} # sort by point value, then word length, then alphabetal
			map { [ $_, $results -> { $_ } ] } # extract what we need to sort by
			keys %{ $results } ){ 
			
			my ($w,$v) = @{ $result };
			if($v ne $lv){ 
				printf "\n%02d ", $v;
			}	
			printf " %s", $w;
			$total += $v;
			$lv = $v;
		}
		printf "\n";
		printf "%.2f point avg\n\n", ( $total / $count );
	}
}
