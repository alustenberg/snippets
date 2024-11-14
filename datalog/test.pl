#!/usr/bin/perl

use strict;
use warnings;
use Carp;

use lib './lib';

use tables;
use datastore;

use Data::Dumper;
use Getopt::Long;
use Config::Std;

$Data::Dumper::Indent = 1;

my $dbh = datastore::init()                 or croak "Cannot init datastore: $!";
my $afr = tables::load('tables/fuel.csv',0) or croak "Cannot load fuel table: $!";
my $sd  = tables::load('tables/sd.csv'  ,0) or croak "Cannot load SD table: $!";
datastore::build_index($dbh)                or croak "Cannot reindex datastore: $!";

#printf "afr table: %s\n", Dumper($afr);

foreach my $test ( [ .9, 2000 ], [ 1.05, 1750 ], [ 1.42, 1750 ], [1.79, 3200]) { 
	printf "value? %f x %f: %f\n", @{ $test }, tables::getValue($afr, @{ $test });
}

#printf "sd  table: %s\n", Dumper($sd);


