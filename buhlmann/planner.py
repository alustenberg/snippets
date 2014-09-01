#!/usr/bin/env python2

import csv
import math
import os
import sys
import yaml

from pprint import pprint

debug = 0
safety_stop = 5

class zh:
	def __init__(self, tissues = None, model='zh-l16b'):
		self.ht      = []
		self.m0      = {}
		self.dm      = {}
		self.a       = {}
		self.b       = {}
		self.tissues = {}

		tab = csv.reader( open("tables/{0}.tsv".format(model)), dialect = 'excel-tab' )
		if( debug >= 2 ):
			print "ht	m0	dm	a	b"
		for row in tab:
			try:
				ht = float(row[0])
				m0 = float(row[1]) / 33.0 # tables are in fsw, crunch in ata
				dm = float(row[2])

				self.ht.append(ht)
				self.m0[ht] = m0
				self.dm[ht] = dm
				self.a[ht]  = m0 - dm * 1 
				self.b[ht]  = 1 / dm 

				if( debug >= 2 ):
					print "{:5.1f}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}".format(
						ht, self.m0[ht], self.dm[ht], self.a[ht], self.b[ht]
					)
			except ValueError:
				pass
			except:
				raise
				
		tab = None

		if not tissues:
			self.tissues = { x: .79 * ( 1.0 - 2.042 / 33.3 ) for x in self.ht }
		else : 
			self.tissues = { x: tissues[x] for x in self.ht }

	def tick(self, start_ata = 1.0, end_ata = 1.0, duration=1.0, tissues = None):
		""" run tissue loading caculations on passed state

		if no pased state, use our own

		"""
		if not tissues:
			tissues = self.tissues


		start_n2_ata = .79 * ( start_ata - 2.042 / 33.3 ) # pp h20
		end_n2_ata   = .79 * ( end_ata   - 2.042 / 33.3 ) 
		diff_n2_ata  = end_n2_ata - start_n2_ata
		delta_n2_ata = 0
		if ( duration > 0 ):
			delta_n2_ata = diff_n2_ata / duration

		#print "n2 start: {:.5f}, n2 end: {:.5f}, d n2 ata {:.5f}".format(
		#	start_n2_ata,
		#	end_n2_ata,
		#	delta_n2_ata
		#	)

		ig_tap  = {}
		ceiling = {}
		ln2 = math.log(2)	
		for ht in self.ht:
			# 0 calc: P = Po + (Pi - Po)(1 - e^-kt).
			# tissues[i] = tissues[i] + ( n2_bar - tissues[i] ) * ( 1 - pow(2, ( - ( seconds / 60 ) / ht[i] )))

			# d calc: P = Pio + c(t - 1/k) - [Pio - Po - (c/k)]e^-kt
			# Pio = initial inspired (alveolar) inert gas pressure
			# (Pio = initial ambient pressure minus water vapor pressure)
			# Po = initial compartment inert gas pressure
			# c = rate of change in inspired gas pressure with change in ambient pressure
			# (this is simply rate of ascent/descent times the fraction of inert gas)
			# R = same as c
			# t = time (of exposure or interval)
			# k = half-time constant = ln2/half-time (same as instantaneous equation)

			c = delta_n2_ata
			t = duration
			po = tissues[ht]
			pio = start_n2_ata
			k = ln2 / ht
			a = self.a[ht]
			b = self.b[ht]


			if ( t > 0):
				tissues[ht] = pio + c * (t - 1.0 / k ) - ( pio - po - ( c / k ) ) * pow(math.e, - k * t) 
				
			#print "ht={:3.0f}, c = {:8.5f}, t={:1.5f}, pio={:2.5f}, po={:2.5f}, pe={:2.5f}, k={:2.5f}, a={:2.5f}, b={:2.5f}".format( 
			#	ht, c, t, pio, po, tissues[ht],k, a, b)
			ig_tap[ht]  = max( ( tissues[ht] - self.a[ht] ) * self.b[ht], 0) 

		return [ tissues, ig_tap ]

	def get_next_stop( self, start_ata, p_m, p_gf_low, p_gf_high, inital_stop, tissues = None, stride = 0.01 ):
		if not tissues:
			tissues = self.tissues

		cur_ata = start_ata

		while cur_ata > 1.0:
			cur_gf = p_gf_low
			if inital_stop:
				# we have an inital stop, increase gf to match
				cur_stop_percentage = ( inital_stop - cur_ata ) / ( inital_stop - 1.0 )
				cur_gf += cur_stop_percentage * ( p_gf_high - p_gf_low )

			for ht in self.ht:
				m_ata  = self.a[ht] + 1.0 / self.b[ht] * cur_ata # m value, ata
				c_p_m  = tissues[ht] / m_ata                # percentage of m

				ip_g   = tissues[ht] - cur_ata              # tissue inert gass pressure gradient
				m_g    = m_ata - cur_ata                   # m value gradient
				c_p_gf = ip_g / m_g                        # percentage m value gradient

				#pprint([cur_n2_ata,m_ata, c_p_m, ip_g, m_g, c_p_gf])
				#print "amb_ata={:.4f} m_ata={:.5f} t_ata={:.5f}".format( cur_ata, m_ata, tissues[ht])
				#print "cpm={:f} pm={:f} ;  c_g_gf={:f} p_gf={:f}".format( c_p_m, p_m, c_p_gf, p_gf )

				if ( p_m != 0 and c_p_m > p_m ) or c_p_gf > cur_gf:
					#print "ata: {:f} ht: {:3.0f} cpm:{:f} pm:{:f} c_g_gf:{:f} p_gf:{:f}".format( 
					#	cur_ata, ht, 
					#	c_p_m, p_m, 
					#	c_p_gf, cur_gf )
					optimal_stop_ata = cur_ata + stride
					return optimal_stop_ata

			
			cur_ata -= stride
		return 1.0

	def plan_stops( self, start_ata, p_m, p_gf_low, p_gf_high, stop_time = 1, metric = False, tissues = None ):
		""" plan stops based on starting ambient ata, %m value, and %gradient factor """
		stops = [ ]
		cur_ata = start_ata
		last_stop = cur_ata
		safety_obligo = safety_stop # 5 minute safety stop
		if not tissues:
			tissues = self.tissues.copy()

		inital_stop = None
		while last_stop > 1.0:
			c_stop_time = stop_time
			opt_stop = self.get_next_stop( last_stop, p_m, p_gf_low, p_gf_high, inital_stop, tissues )
			n_stop = opt_stop
			
			
			if metric:
				pass
			else:
				interval = 5.0
				n_stop_act_fsw = ( n_stop - 1.0 ) * 33.0 
				n_stop_fsw = math.ceil( n_stop_act_fsw / interval ) * interval
				if n_stop_act_fsw <= 15:
					if safety_obligo >= 0:
						n_stop_fsw = 15
						c_stop_time = 1
						safety_obligo -= 1
					elif n_stop_act_fsw > 0.0:
						n_stop_fsw = 15
					else:
						n_stop_fsw = 0

				n_stop = 1.0 + ( n_stop_fsw / 33.0 ) 
		

			if n_stop > cur_ata:
				raise RuntimeError("increasing stop depth: {:f} vs {:f}".format( n_stop, cur_ata ))

			if last_stop and ( abs(opt_stop - last_stop ) < .01):
				raise RuntimeError("stalled ascent")

			if not inital_stop:
				inital_stop = n_stop
		
			self.tick(last_stop, n_stop, c_stop_time, tissues )
			if n_stop != last_stop:
				c_stop_time = int( math.ceil( abs( last_stop - n_stop ) / 1.0 ) ) 
				stops.append( [ last_stop, n_stop, c_stop_time ] )
			else:
				stops.append([ n_stop, c_stop_time])
			last_stop = n_stop

		return stops

class dive:

	def __init__(self, mvalue=0.8, gf_low = .3, gf_high = 0.3, ceiling = 1.0, rmv = 0.7, previous = None, tanks = None):
		tissues = None
		if not tanks:
			raise RuntimeException("need tanks")

		if previous:
			tissues = previous.zh.tissues

		self.zh      = zh( tissues )
		self.mvalue  = float(mvalue)
		self.gf_low  = float(gf_low)
		self.gf_high = float(gf_high)
		self.max_tap = float(ceiling)  # tolerated ambient pressure, 1.0 == no deco, 0 == no limit
		self.rmv     = float(rmv)
		self.tanks   = tanks

	def get_cap(self):
		return sum([ x['capacity'] * ( x['fill'] - x['reserve'] ) / x['rate'] for x in self.tanks ] )

	def get_rem_psi(self, cf_used):
		total_cf =  sum([ x['capacity'] * x['fill'] / x['rate'] for x in self.tanks ] )
		system_fill = max([ x['fill'] for x in self.tanks ])
		return system_fill * ( total_cf - cf_used ) / total_cf
		

	def get_stops_gas_factor( self, stops ):
		""" plan stops, sum rmv multipliers per minute. """
		factor = 0.0
		for [ s_ata, e_ata, time] in stops:
			if s_ata == e_ata == ( ( 15.0 / 33.0 ) + 1 ) :
				continue
			if debug > 3:
				print "stop: {:.5f} ~ {:.5f} for {:1f}".format(
					s_ata,
					e_ata,
					time)
			factor += ( ( s_ata + e_ata ) / 2.0 ) * time
		return factor
	

	def add_travel_nodes( self, dive_plan, delta_rate = 1.0, in_progress = False):
		""" takes 2 tuple list of [ depth, time ] waypoints, 
		converts to 3 tuple of [ start, end, time ] 
		adds inital state
		add travel nodes between waypoints
		consolidates repeat nodes"""


		if len(dive_plan) == 0:
			return dive_plan

		act_dive_plan = [ [ 1.0, 1.0, 0 ] ] # start at ambient
		if in_progress:
			# unless we're in progress..
			if len(dive_plan[0]) == 3:
				act_dive_plan = [ dive_plan[0] ]
			else:
				act_dive_plan = [ [ dive_plan[0][0], dive_plan[0][0], dive_plan[0][1] ] ]

			dive_plan = dive_plan[1:]

		# add in travel stops
		for entry in dive_plan:
			if len(entry) == 3:
				# already a three tuple. chuck it and move on 
				act_dive_plan.append(entry)
				continue
				
			e_depth = entry[0]
			ls_depth = act_dive_plan[-1][0]
			le_depth = act_dive_plan[-1][1]
			if e_depth == ls_depth == le_depth: 
				# prior steady stop, repeat waypoint. fold into last entry
				act_dive_plan[-1][2] += entry[1]
			elif e_depth == le_depth: 
				# prior asc/dsc node, but at dest.
				act_dive_plan.append( [ e_depth, e_depth, entry[1] ] )
			else:
				# we're not where we should be
				act_dive_plan.append( [
					le_depth,
					e_depth,
					int( math.ceil( abs(le_depth - e_depth) / delta_rate ) ) ] )

				# get there, and add our waypoint
				act_dive_plan.append( [ e_depth, e_depth, entry[1] ] )
				
				
		return act_dive_plan 



	def plan( self, dive_plan, name = 'unknown'):
		""" actually plan the dive."""
		print "---"
		quiet = False
		if ( len(dive_plan) == 1 and dive_plan[0][0] == 1.0 ):
			# surface interval. 
			quiet = True
			print "si:\t{:.0f} min".format(dive_plan[0][1])
		else:
			print "dive:\t{:s}".format(name)
			print "gf:\t{:.2f} /\t{:.2f}\t%m: {:.2f}\tceil: {:2.1f}".format(
				self.gf_low,
				self.gf_high,
				self.mvalue,
				self.max_tap

			)

		depth_ata = 1.0

		travel_plan = self.add_travel_nodes( dive_plan )
		stops = [] # last set of obligated stops
		l_tap = {} # last known set of tolerated ambient pressures
		wallclock = 0

		gas_consumed = 0

		if ( debug >= 2 ):
			pprint(dive_plan)
			pprint(travel_plan)

		if not quiet:
			print "run\tfsw out\tps out\ttime\tstate\tht\tceil\ttense\tnotes"
			print "{:d}\t{:.0f}\t{:.0f}\t{:d}\t{:s}\t{:3.1f}\t{:5.1f}\t{:5.2f}\t{:s}".format(
				0,
				0,
				self.get_rem_psi( gas_consumed ),
				0,
				'surf',
				0,
				0,
				0,
				'')

		for [ s_depth_ata, e_depth_ata, time ] in travel_plan:
			avg_depth_ata = ( s_depth_ata + e_depth_ata ) / 2.0

			state = '~'
			if time:
				delta_ata = ( e_depth_ata - s_depth_ata ) / time
				if s_depth_ata < e_depth_ata:
					state = '+{:.0f}'.format(delta_ata * 33.0)
				elif s_depth_ata > e_depth_ata:
					state = '{:.0f}'.format(delta_ata * 33.0)

			bail_reason = ""
			c_time = time
			# only do the iteration check on fixed depths.  if start != end, its a travel node.
			while c_time and ( s_depth_ata == e_depth_ata ):
				# run a test against the tissues to see if they can sustain current exposure
				tissues = self.zh.tissues.copy() 
				( new_tissues, tap ) = self.zh.tick( 
					start_ata = s_depth_ata, 
					end_ata = e_depth_ata, 
					duration = c_time, 
					tissues = tissues )
				
				stops = self.zh.plan_stops(depth_ata, self.mvalue, self.gf_low, self.gf_high, tissues = new_tissues.copy() )
				stops = self.add_travel_nodes( dive_plan = stops, in_progress = True)
				stop_factor = self.get_stops_gas_factor( stops )

				gas_required = 0 # default to surface
				gas_available = 0 
				if avg_depth_ata > 1.0 :
					# rb_gas_requiered
					# ascent gas (stop factor) + trouble shoot gas ( current avg ata * 2 min) * panic shared rmv of 2.0
					rb_gas_required = stop_factor * 2.0 + avg_depth_ata * 1.0 * 2.0

					# gas required for this segment
					c_gas_required = avg_depth_ata * self.rmv * c_time
					
					gas_required = rb_gas_required + c_gas_required

					gas_available = self.get_cap() - gas_consumed

				# check our deco limits.  
				l_tap = max( tap.values() )

				if gas_required and gas_required > gas_available:
					bail_reason = "rock bottom ({:d} of {:d} min planned)".format( 
						c_time, time )
				elif self.max_tap and l_tap > self.max_tap:
					bail_reason = "deco limit ({:d} of {:d} min planned)".format(c_time,time)
				else:
					break # we're ok

				# 1 minute stop, bail
				if c_time == 1:
					break

				# otherwise, try a shorter time
				c_time -= 1

			# actually apply the exposure
			if c_time:

				( new_tissues, l_tap ) = self.zh.tick( 
					start_ata = s_depth_ata, 
					end_ata   = e_depth_ata, 
					duration  = c_time  )

				gas_in = gas_consumed
				if avg_depth_ata > 1.0:
					gas_consumed += avg_depth_ata * self.rmv * c_time
					if debug > 1:
						print "gas consumed: {:.2f}\t{:.2f}\t{:d}\t{:.5f}".format(
							avg_depth_ata,
							self.rmv,
							c_time,
							gas_consumed )
		
				if not quiet:
					k = sorted( l_tap, key = l_tap.get, reverse = True )[0]
					print "{:d}\t{:.0f}\t{:.0f}\t{:d}\t{:s}\t{:3.1f}\t{:5.1f}\t{:5.2f}\t{:s}".format(
						wallclock + c_time,
						( e_depth_ata - 1.0 ) * 33.0,
						self.get_rem_psi( gas_consumed ),
						c_time,
						state,
						k,
						( l_tap[k] - 1.0 ) * 33.0,
						( new_tissues[k] - e_depth_ata ),
						bail_reason)
				
				wallclock += c_time

			depth_ata = e_depth_ata

		#pprint(stops)
		# now do our stop obligations
		for [ s_depth_ata, e_depth_ata, c_time ] in stops:
			if c_time == 0:
				continue	
			
			avg_depth_ata = ( s_depth_ata + e_depth_ata ) / 2.0
			
			state = 'stop'
			if c_time:
				delta_ata = ( e_depth_ata - s_depth_ata ) / c_time
				if s_depth_ata < e_depth_ata:
					state = '+{:.0f}'.format(delta_ata * 33.0)
				elif s_depth_ata > e_depth_ata:
					state = '{:.0f}'.format(delta_ata * 33.0)

			( new_tissues, l_tap ) = self.zh.tick( 
				start_ata = s_depth_ata, 
				end_ata   = e_depth_ata, 
				duration  = c_time  )

			gas_in = gas_consumed
			gas_consumed += avg_depth_ata * self.rmv * c_time
			if debug > 1:
				print "gas consumed: {:.2f}\t{:.2f}\t{:d}\t{:.5f}".format(
					avg_depth_ata,
					self.rmv,
					c_time,
					gas_consumed )
			
			if not quiet:
				k = sorted( l_tap, key = l_tap.get, reverse = True )[0]
				print "{:d}\t{:.0f}\t{:.0f}\t{:d}\t{:s}\t{:3.1f}\t{:5.1f}\t{:5.2f}\t{:s}".format(
				#print "{:d}\t{:d}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:d}\t{:s}\t{:3.1f}\t{:5.1f}\t{:5.2f}\t{:s}".format(
					wallclock + c_time,
					( e_depth_ata - 1.0 ) * 33.0,
					self.get_rem_psi( gas_consumed ),
					c_time,
					state,
					k,
					( l_tap[k] - 1.0 ) * 33.0,
					( new_tissues[k] - e_depth_ata ),
					'')

			wallclock += c_time

		num_leading = 4 
		k = sorted( l_tap, key = l_tap.get, reverse = True )[:num_leading]
		a_tap = sum([       l_tap[ht] for ht in k ])  / len(k)
		a_tis = sum([ new_tissues[ht] for ht in k ])  / len(k)

		print ""
		print "ht\tppn2\tceil"
		surf_n2pp = .79 * ( 1.0 - 2.042 / 33.3 )
		for ht in k:
			print "{:5.1f}\t{:2.3f}\t{:6.1f}".format(
				ht, 
				new_tissues[ht],
				( l_tap[ht] - 1.0 ) * 33.0 

			)

		#print "leading tissues: " + " ".join( ["{:.0f}:{:.3f}".format( ht, new_tissues[ht] ) for ht in k ]  )
		#print "leading ceiling: " + " ".join( ["{:.0f}:{:.3f}".format( ht,       l_tap[ht] ) for ht in k ]  )
		print "avg\t{:2.3f}\t{:6.1f}\tt:{:.0f}\tpsig:{:.0f}".format(
			a_tis,
			( a_tap - 1.0 ) * 33.0,
			wallclock,
			self.get_rem_psi( gas_consumed ))
		print ""


	def _run_plan( self ):
		pass

	def _get_plan_score( self ):
		pass
	
class mission:
	dives = []
	plan  = {}
	def __init__(self):
		pass

	def load(self, planname, overrides):
		d = yaml.load(open("./plans/default.yaml").read(8192))
		p_data = open("./{0}".format(planname)).read(8192)
		for x in os.environ.keys():
			p_data = p_data.replace(":%s:" % x.lower(), os.environ[x])

		p = yaml.load(p_data)
		
		self.plan = {}
		# merge our options between default, planname, and overriden paramaters
		for k in d.keys():
			if k in overrides and getattr(overrides,k) != None:
				self.plan[k] = getattr(overrides,k)
			elif p.has_key(k):
				self.plan[k] = p[k]
			else:
				self.plan[k] = d[k]

		# load tank configs
		tanks = []
		for t in self.plan['tanks']:
			t_data = yaml.load(open("tanks/{0}.yaml".format(t)))
			t_data['name'] = t
			tanks.append(t_data)
		self.plan['tanks'] = tanks
		#pprint(self.plan)

	def run(self):
		last_dive = None
		for stage in self.plan['dives']:
			c_dive = dive( 
				previous = last_dive, 
				mvalue   = self.plan['m-value'], 
				gf_low   = self.plan['m-gf-low'], 
				gf_high  = self.plan['m-gf-high'],
				ceiling  = self.plan['ceiling'],
				tanks    = self.plan['tanks'],
				rmv      = self.plan['rmv'])

			dive_plan = [ [ ( x[0] / 33.0 ) + 1.0, x[1] ] for x in stage['plan'] ] 


			tank_id = ", ".join( [ x['name'] for x in self.plan['tanks'] ] )
			c_dive.plan( dive_plan, stage['name'] + " " + tank_id )
			self.dives.append( c_dive )
			last_dive = c_dive

	def render(self, output_dir ):
		pass

if __name__ == '__main__':
	import argparse

	argp = argparse.ArgumentParser( description = 'air calculations' )
	argp.add_argument( 'plan'      , metavar='plan' , nargs='+', type=str,   default=["plans/default.yaml"], help="plan name(s)" )
	argp.add_argument( '--tanks'  , dest='tanks'    , nargs='+', type=str,   default=None     , help="Tanks (BT, [ al80 ])" )
	argp.add_argument( '--rmv'    , dest='rmv'      , nargs='?', type=float, default=None     , help="Respiratory Minute Volume (BT, .75 cf/min)" )
	argp.add_argument( '--stop'   , dest='stop'     , nargs='?', type=int  , default=5        , help="Safety stop time (minutes, 5)" )
	argp.add_argument( '--ceiling', dest='ceiling'  , nargs='?', type=float, default=None     , help="Deco ceiling limit   ( BT, .8 ATA )" )
	argp.add_argument( '--gf-high', dest='m-gf-high', nargs='?', type=float, default=None     , help="gradient factor high ( ASC )" )
	argp.add_argument( '--gf-low' , dest='m-gf-low' , nargs='?', type=float, default=None     , help="gradient factor low  ( ASC )" )
	argp.add_argument( '--m-value', dest='m-value'  , nargs='?', type=float, default=None     , help="percentage m-value   ( ASC )" )
	argp.add_argument( '--output ', dest='output'   , nargs='?', type=str,   default="output" , help="output directory " )
	argp.add_argument( '--verbose','-v', action='count'     , default=0,     help="Verbose (false)")
	
	args = argp.parse_args()
	
	debug       = args.verbose
	safety_stop = args.stop

	for plan in args.plan:
		print "---\nplan:\t{:s}".format(plan)
		m = mission()
		m.load(planname = plan, overrides = args)
		m.run()
	#m.render( args.output )
	
