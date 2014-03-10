#!/usr/bin/perl

use strict;
use warnings;
use Carp;

use lib './lib';

use tables;
use datastore;

# flush output on every print
local $| = 1;

use Data::Dumper;
use Getopt::Long;
use Config::Std;


# wooo, globals
my ( %config );

my $config_file = "datalog.conf";
my $debug = 0;
my $datalogRequiredFields = [
	'RPM',
	'LOAD',
	'LOADX',
	'AFR',
	'LTFT1',
	'STFT1',
	'TS',
];

read_config( $config_file => %config ) or croak "Cannot read configuration";

my $log_dir = $config{ '' }{ datadir }   || 'logs';
my $subdiv  = $config{ '' }{ subdivide } || 0;

GetOptions( 
	"sub=i" => \$subdiv,
);


my $afr = tables::load('./tables/fuel.csv',$subdiv) or croak "Cannot load fuel table: $!";
my $sd  = tables::load('./tables/sd.csv'  ,$subdiv) or croak "Cannot load SD table: $!";

my $dbh = datastore::init() or croak "Cannot init datastore: $!";
# slurp data logs 
for( sort glob( $log_dir . "/*.csv" ) ) { 
	loadCSV( $_, $datalogRequiredFields );
}
	
datastore::build_index($dbh);
renderTableDeltas();

sub loadCSV { 
	# take a CSV, dump into the db
	my ($file, $requiredFields) = @_;
	printf STDERR "loading %s\n", $file;

	my $insert = $dbh -> prepare(<<'SQL') or croak "Cannot prepare statement : $!";
insert into logs ( 
	RPM,
	LOAD,
	LOADX,
	AFR,
	STFT,
	LTFT,
	TS,
	TARGET
) values (?,?,?,?,?,?,?,?);
SQL

	open(my $fh, "<", $file) or croak "Cannot open file: $!";
	seek($fh,0,0) or croak "Cannot seek: $!";

	my $csv = Text::CSV -> new() or croak "Cannot create CSV: $!";
	my $header = $csv -> getline( $fh );
	$csv -> column_names( @{ $header } );
	
	my $cols = { map { $_ => 1 } @{ $header } };
	foreach my $required ( @{ $requiredFields } ) { 
		if ( not exists $cols -> { $required } ){ 
			croak "missing required field $required in datalog $file";
		}
	}
	
	# this.. really should be done driven off the config values in the delay segment
	my @wbo2roll = map { 14.7 } ( 0..( $config { 'delay' } { WBO2 } || 1) );
	
	while(my $row = $csv -> getline_hr( $fh ) ) { 
		push @wbo2roll, $row -> { AFR  };
		$row -> { AFR  } = shift @wbo2roll;

		$insert -> execute( 
			$row -> { RPM }, 
			$row -> { LOAD },
			$row -> { LOADX },
			$row -> { AFR },
			$row -> { STFT1 },
			$row -> { LTFT1 },
			$row -> { TS },
			tables::getValue( $afr, $row -> { LOAD }, $row -> { RPM } )
		) or croak "Cannot insert data: $!";
	}
	
	close($fh) or croak "Cannot close: $!";
	return;
}


sub renderTableDeltas { 
	printf "AFR vs fuel table\n";
	renderTable($afr,'LOAD' , 'afr');

	printf "STFT vs SD multipler\n";
	renderTable($sd,'LOADX' , 'STFT');

	printf "AFR vs SD multipler\n";
	renderTable($sd ,'LOADX', 'afr');

	printf "AFR skew vs SD multipler\n";
	renderTable($sd ,'LOADX', 'skew');
	return;
}

sub renderTable { 
	my ($table,$idx, $output) = @_;

	my ($rows, $cols, $data ) = @{ $table };
	
	my $skew = $config{ '' }{ diffmultiplier } || 1.0;

	my $dig = $dbh -> prepare(<<"SQL") or croak "Cannot prepare: $!";
select 
	avg(AFR) afr, 
	avg(STFT) STFT,
	avg(LTFT) LTFT,
	
	avg(AFR - TARGET) * $skew skew,
	count(*) num 
from logs 
	where $idx >= ? 
	and $idx < ? 
	and RPM >= ? 
	and RPM < ?
	and TS >= 0;
SQL

	my $last_row = $rows -> [0];

	my @o_buff = (); # output buffer, since we work low -> high, but want to output high -> low

	push @o_buff, [ sprintf ( "%5s", $idx ) , map { sprintf "%5d", $_ } @{ $cols } ];

	foreach my $r(0..scalar ( @{ $rows } ) -1) { 
		my $row = $rows -> [$r];
		my $next_row = $rows -> [$r+1] || $rows -> [$r];

		#printf "%2.2f ", $row;
		push @o_buff, [ sprintf "%2.2f ", $row ]; # push array ref with our row header
		
		my $last_col = $cols -> [0];

		foreach my $c (0..scalar ( @{ $cols } ) -1 ) { 
			my $col = $cols -> [$c];
			my $next_col = $cols -> [$c+1] || $cols -> [$c];

			# since each 'bin' is actually a point, avg everything in from around it
			my @args = ( 
				$row + ( $row - $last_row ) / 2,
				$row - ( $next_row - $row ) / 2,
				$col - ( $col - $last_col ) / 2,
				$col + ( $next_col - $col ) / 2
			);

			#printf "fetch : %s\n", Dumper(\@args);
			$dig -> execute(@args) or croak "Cannot execute";
			
			while( my $entry = $dig -> fetchrow_hashref() ) { 
				#printf "%s,%s = %.02f x %d\n", $row, $col, $entry -> { afr } || 0, $entry -> { num } || 0;
				if( $entry -> { num } >= $config{ '' }{ minsamples } ) { 
					#printf ", %4.1f", $entry -> { afr };
					push @{ $o_buff[-1] }, sprintf "%5.1f", $entry -> { $output };
				} else { 
					push @{ $o_buff[-1] }, sprintf "     ";
					#printf ", -   ";
				}
			}
			$last_col = $col;
		}
		#printf "\n";
		$last_row = $row;
	}
	foreach my $o_row ( @o_buff ) { 
		printf "%s\n", join(",", @{ $o_row } );
	}

	return;
}

