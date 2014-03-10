#!/usr/bin/env python

import math
import argparse

argp = argparse.ArgumentParser( description = 'air calculations' )
argp.add_argument( '--rmv','-r' , nargs='*', type=float, default=[0.75], help="Respiratory Minute Volume (.7)" )
argp.add_argument( '--capacity' , nargs='*', type=float, default=[77.8], help="Tank capacity (78, AL80)" )
argp.add_argument( '--pressure' , nargs='?', type=float, default=3000,   help="Capacity pressure (3000psi)" )
argp.add_argument( '--depth'    , nargs='*', type=float, default=[60],   help="Depth (60')" )
argp.add_argument( '--rate'     , nargs='?', type=float, default=30.0,   help="decent rate (30 fpm)")
argp.add_argument( '--ascent'   , nargs='?', type=float, default=30.0,   help="acent rate (30 fpm)")
argp.add_argument( '--noopt'    , action='store_true',                   help="skip optional stop time (false)")
argp.add_argument( '--fast'     , action='store_true',                   help="fast ascents (30fpm linear) (false)")

argp.add_argument( '--stopdepth', nargs='?', type=float, default=15.0,   help="safety stop depth")
argp.add_argument( '--stop'     , nargs='?', type=float, default=3.0,    help="safety stop time (3 min)")
argp.add_argument( '--problem'  , nargs='?', type=float, default=1.0,    help="rock bottom problem time (1 min)")
argp.add_argument( '--stress'   , nargs='?', type=float, default=2.0,    help="Stress RMV (2.0)")
argp.add_argument( '--reserve'  , nargs='?', type=float, default=250,    help="Additional Reserve pressure (250psi)" )

argp.add_argument( '--plan'   ,'-p', action='store_true',                help="Print detail plan (false)")
argp.add_argument( '--short'  ,'-s', action='store_true',                help="short (summary) output (false)")
argp.add_argument( '--pony'   ,      action='store_true',                help="Pony calculations, start at depth (false)")
argp.add_argument( '--verbose','-v', action='count'     , default=0,     help="Verbose (false)")

# zh-l16 factors
argp.add_argument( '--loading','-l', nargs='*', type=float, default = [ ], help="tissue compartment init loading (bar, based on altitude)" )
argp.add_argument( '--alt'    ,'-a', nargs='?', type=int  , default = 0  , help="Altitude (0ft)" )
argp.add_argument( '--ceiling','-c', nargs='?', type=float, default = -10, help="Minium deco ceiling. (-10 fsw)" )
argp.add_argument( '--fuse'   ,'-f', nargs='?', type=int  , default = None , help="NDL fuse ascent depth (1/2)" )
argp.add_argument( '--diff'   ,      action='store_true',                  help="output ceiling diffs (false)")

argp.add_argument( '--interval', nargs='?', type=int  , default = 0 , help="surface interval (0 min)" )


# simulation tweaks
argp.add_argument( '--ticks'  ,'-t', nargs='?', type=int  , default = 1  , help="simulation tick per minute (1)" )


args = argp.parse_args()

debug = args.verbose
if ( debug >= 1):  
	print args

def depth_factor ( depth ): 
	factor = ( ( depth / 33.0 ) + 1.0 )

	if ( debug >= 4 ):
		print "depth factor {:.2f} for {:.2f} depth".format(
			factor,
			depth
			)
	return factor

def usage_minute ( depth, rmv ): 
	usage = depth_factor( depth ) * rmv
	if ( debug >= 3 ):
		print "usage minute {:.2f} ft2 for {:.2f} rmv @ {:.0f} ft".format(
			usage,
			rmv,
			depth
			)
	return usage

def vol_to_pressure ( vol, cap, pres): 
	vol_pres = ( vol * ( pres / cap ) )
	if ( debug >= 2 ):
		print "{:.2f} ft2 -> {:.2f} pres".format(
			vol,
			vol_pres
			)
	return vol_pres

def calc_rockbottom ( depth, rmv,  prob_time, ss_time, asc_rate ):
	prob_gas = usage_minute(         depth, rmv ) * prob_time
	ss_gas   = usage_minute(args.stopdepth, rmv ) * ss_time
	if ( depth <= args.stopdepth):
		ss_gas   = 0.0 # already at the safety stop
		prob_gas = 0.0 # just ascent from SS rather then problem solving

	asc_time = depth / asc_rate 
	asc_gas  = usage_minute( depth / 2.0, rmv ) * asc_time
	tot_gas  = prob_gas + ss_gas + asc_gas;

	if ( debug >= 2 ):
		print "calc_rockbottom({:.0f}, {:.2f}, {:.1f}, {:.1f}, {:.0f}) -> ( prob ft2 {:.2f} + stop ft2 {:.2f} + ascent ft2 {:.2f} ) = {:.2f}".format(
			depth,
			rmv,
			prob_time,
			ss_time,
			asc_rate,
			prob_gas,
			ss_gas,
			asc_gas,
			tot_gas
		)

	return tot_gas

def calc_max( depth, rmv, stress_rmv, problem_time, stop_time, ascent_rate, capacity, pressure, reserve):
	gas = calc_rockbottom( 
		depth, 
		stress_rmv,
		problem_time, 
		stop_time,
		ascent_rate
		)

	psi = vol_to_pressure(
		gas, 
		capacity, 
		pressure 
		)

	print "rockbottom @ {:3.0f} with {:.2f} RMV is {:.2f} ft^2, {:.0f} psig".format(
		depth,
		stress_rmv,
		gas,
		psi + reserve
		)

def calc_zh( load, current_bar, seconds = 60 ):
	n2_bar = ( .79 ) * current_bar

	ht = [    4.0,    8.0,  12.5,  18.5,  27.0,  38.3,  54.3,  77.0, 109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0 ]
	a  = [ 1.2599, 1.0000, .8618, .7562, .6200, .5043, .4410, .4000, .3750, .3500, .3295, .3065, .2835, .2610, .2480, .2327 ]
	b  = [  .5050,  .6514, .7222, .7825, .8126, .8434, .8693, .8910, .9092, .9222, .9319, .9403, .9477, .9544, .9602, .9653 ]

	# tolerated ambient pressure
	tap = [ 0.0 for x in range(16) ]
	ceiling   = [ 0.0 for x in range(16) ]


	for i in xrange(16):
		if seconds > 0:
			load[i] = load[i] + ( n2_bar - load[i] ) * ( 1 - pow(2, ( - ( seconds / 60 ) / ht[i] )))
		# inert gas tolerated ambient pressure
		ig_tap  = ( current_bar / b[i] ) + a[i]
		# tolerated ambient pressure
		tap     = max( ( load[i] - a[i] ) * b[i], 0)
		ceiling[i] = ( tap - 1.000 ) * 33.0

	return ceiling

def calc_plan( depth, rmv, stress_rmv, problem_time, stop_time, ascent_rate, capacity, pressure, reserve, si):
	# now we get into more interesting stuff
	c_cap   = capacity # start with a full tank
	c_depth = 0      # start at surface
	r_cap   = reserve * ( capacity / pressure )
	stop_commit = 0 # safey stop commitment time, set to stop_time once we hit 30'
	if( depth >= 30 ): 
		stop_commit = stop_time

	minutes = 0      # 0 minute
	state   = 'down'
	s_min   = 0 

	rb        = calc_rockbottom( depth, stress_rmv , problem_time, stop_commit, ascent_rate )
	rb_psi    = vol_to_pressure( rb, capacity, pressure ) + reserve
	avail_psi = pressure - rb_psi
	thirds    = avail_psi / 3.0
	turn_psi  = pressure - thirds

	if ( args.pony ):
		c_depth = depth
		state = 'back'


	lz_n2 = [ 0.79 for x in range(16) ]
	ceil = calc_zh ( lz_n2, depth_factor( c_depth ), 0 ) # dummy run the zh to check for dec
	last_ceil = ceil
	ndl_fuse = False

	lineformat =  "{:3},{:4.0f},{:5.1f},{:5.2f},{:6.2f},{:6.2f},{:5.0f},{:5.0f}, {:4s},{:4d}, {:7.2f},{:7.2f},{:7.2f},{:7.2f}, {:7.2f},{:7.2f},{:7.2f},{:7.2f}"
	print         "min, fsw, dfsw,  rmv,  rbcf, remcf, psig,rbpsi,state,smin,      c1,     c2,     c3,     c4,      c5,     c6,     c7,     c8"

	print lineformat.format(
		0,
		0,
		0,
		rmv,
		rb,
		c_cap,
		pressure,
		rb_psi,
		'surf',
		1,
		*ceil[0:8]
		)

	while(True):
		minutes += 1
		# starting depth
		s_depth = c_depth 
		l_state = state

		# calc our rockbottom to see what needs to happen this iteration
		psig    = vol_to_pressure( c_cap     , capacity, pressure )
		psi_use = psig - rb_psi
		
		ceil = calc_zh ( lz_n2, depth_factor( c_depth ), 0 ) # dummy run the zh to check for dec
		ceil.sort()
		ceil_limit = ceil[-1]
		if ( not ndl_fuse and ceil_limit >= args.ceiling and state != 'ndup'): 
			if state == 'hold' and s_min < stop_time:
				pass
			elif not args.fuse:
				ndl_fuse = max(depth * 1.0 / 2.0, args.stopdepth)
				if ndl_fuse % 5:
					ndl_fuse -= ndl_fuse % 5
					ndl_fuse += 5
			elif c_depth > args.fuse:
				ndl_fuse = args.fuse
			elif c_depth > args.stopdepth:
				ndl_fuse = args.stopdepth
			else:
				print "unhandled fuse state"
			if (debug >= 1) and ndl_fuse:
				print "fuse depth {}".format(ndl_fuse)
		
		if ( ndl_fuse and c_depth > ndl_fuse ):
			asc_rate = args.ascent
			if not args.fast:
				asc_rate = min(args.ascent, depth * .20 )
			
			c_depth  = max(ndl_fuse, depth - asc_rate)
			depth    = c_depth
			rb       = calc_rockbottom( depth, stress_rmv, problem_time, stop_time, ascent_rate) 
			state    = 'ndup'
			if ( c_depth <= ndl_fuse ):
				ndl_fuse = False
				c_state = 'hold'

		# fuzz factor.  used to keep the loop logic slightly saner.  +1 min of current rmv
		# basicly a 'look ahead' for the consumtion of this iter
		fuzz    = 1.0 * rmv * depth_factor ( depth ) 
		while ( ( fuzz + rb + r_cap ) > c_cap and c_depth > 0 ) :
			if args.fast and c_depth > args.stopdepth:
				c_depth = max( args.stopdepth, depth - args.ascent)
			else:
				c_depth  = depth - 0.1
			depth    = c_depth # set depth to current depth, as we're going up
			rb       = calc_rockbottom( depth, stress_rmv, problem_time, stop_time, ascent_rate) 
			state    = 'rbup'
			if(debug >= 1):
				print "asc, new rb: {:5.2f}/{:5.2f}, depth: {:5.1f}".format(
					rb,
					( c_cap - r_cap ),
					depth
				)

		if ( state in ['rbup','ndup'] and (s_depth == c_depth) ):
			state = 'hold'
			
		if ( state == 'down' and ( c_depth == depth) ):
			state = 'out'

		if ( c_depth < depth ): # not deep enough
			c_depth += ascent_rate
			if( c_depth >= depth ):
				c_depth = depth # too deep

		if ( state == 'out' and psig <= turn_psi):
			state = 'back'

		# consume the air
		c_cap -= usage_minute( c_depth, rmv )
		psig   = vol_to_pressure( c_cap, capacity, pressure )
		rb     = calc_rockbottom( depth, stress_rmv , problem_time, stop_commit, ascent_rate )

		ceil = calc_zh( lz_n2, depth_factor(  c_depth ) )


		if ( ( state == 'stop' ) and ( s_min >= args.stop ) ):
			if args.noopt:
				state = 'asup'
			else:	
				state = 'opt'
		
		if( state == 'asup' ):
			depth = c_depth = max( c_depth - ascent_rate, 0 )

		if ( ( state != 'opt' )  and ( abs(args.stopdepth - c_depth) < 0.1 ) ):
			state = 'stop'

		if ( depth < 0 ): 
			c_depth = depth = 0
			state = 'surf'

		if ( l_state != state ):
			s_min = 0
		s_min += 1
	
		ceil_out = ceil[0:8]
		if args.diff:
			ceil_out = [ last_ceil[x] - ceil[x] for x in range(8) ]
		if( ( not args.short ) or ( s_min == 1 ) ):
			print lineformat.format(
				minutes,
				c_depth,
				( c_depth - s_depth ),
				usage_minute( c_depth, rmv ),
				rb,
				c_cap,
				psig,
				vol_to_pressure( rb, capacity, pressure ) + reserve,
				state,
				s_min,
				*ceil_out
				)

			last_ceil = ceil
		if ( 0 == depth ):
			break
	load_format = "{:.3f} {:.3f} {:.3f} {:.3f}  {:.3f} {:.3f} {:.3f} {:.3f}  {:.3f} {:.3f} {:.3f} {:.3f}  {:.3f} {:.3f} {:.3f} {:.3f}"

	if( args.interval ):
		print ""

		i_format = "{:4d} {:6.2f} {:6.2f} {:6.2f} {:6.2f}  {:6.2f} {:6.2f} {:6.2f} {:6.2f}  {:6.2f} {:6.2f} {:6.2f} {:6.2f}  {:6.2f} {:6.2f} {:6.2f} {:6.2f}"
		for i in xrange(0,args.interval+1):
			ceil = calc_zh( lz_n2, 1.000)
			rel = [ 100 * ( x - .79 ) / .79 for x in lz_n2 ] 
			if ( not args.short or i in [ 0, args.interval ] ):
				ceil_out = ceil
				if args.diff:
					ceil_out = [ last_ceil[x] - ceil[x] for x in range(16) ]
				
				print i_format.format(
					i,
					*ceil_out
				)
				last_ceil = ceil
		
	print ""	
	print "--loading " + load_format.format(*lz_n2)
	print ""


for rmv in args.rmv:
	for capacity in args.capacity:
		for depth in args.depth:
			if(debug >= 1 ):
				print "calculating {} depth with {} capacity and {} RMV".format(
					depth,
					capacity,
					rmv
					)

			if ( args.plan ) :
				calc_plan( 
					depth,
					rmv,
					args.stress,
					args.problem,
					args.stop,
					args.rate,
					capacity,
					args.pressure,
					args.reserve,
					args.interval
				)
			else:
				calc_max(
					depth,
					rmv,
					args.stress,
					args.problem,
					args.stop,
					args.rate,
					capacity,
					args.pressure,
					args.reserve
					)
