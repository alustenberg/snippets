#!/usr/bin/env python
import zlib
import argparse
import base64
import hashlib
import json
import math
import random

debug = 0

def chksum(string, salt):
	m = hashlib.md5()
	m.update(string)
	m.update(salt)
	return m.hexdigest()

def freeze(obj, salt, level = 1):
	j = json.dumps(obj)
	c = chksum(j,salt)
	payload = "%s:%s" % ( c, j )
	c = zlib.compress(payload, level)
	b = base64.standard_b64encode(c) 
	return b


def thaw(string, salt):
	c = base64.standard_b64decode(string)
	payload = zlib.decompress(c)
	(h, j) = payload.split(":",1)
	c = chksum(j, salt)

	if( h != c):
		raise InvalidChecksum
	
	obj = json.loads(j)
	return obj

def randv( strlen ):
	c = ""
	for ch in xrange(0,strlen):
		c += chr(random.randint(49,122))
	return c

def sizetest(maxsize = 2048, keysize = 4, payload = 8, level = 1, noheader = 0 ):
	items = {} 
	salt = "foobar"

	endcount = 0

	fstr = "{:3},{:3},{:5},{:2},{:4}"

	if ( not noheader ):
		print fstr.format(
			'key',
			'val',
			'  max',
			' z',
			'items'
		)

	while True:
		i = randv( keysize )
		c = randv( payload )
		
		items[i] = c

		f = freeze(items, salt, level)
		chk = thaw(f, salt)

		if len(f) >= maxsize:
			break

	print fstr.format(
		keysize,
		payload,
		maxsize,
		level,
		len(items)
	)
	return len(items)

if __name__ == "__main__":
	argp = argparse.ArgumentParser( description = 'key-value stuffing into browser cookies' )
	argp.add_argument( '--maxsize' ,'-m', nargs='*', type=int, default=[2048], help="max cookie size (2048)")
	argp.add_argument( '--level'   ,'-z', nargs='*', type=int, default=[0]   , help="compression levels (0)")
	argp.add_argument( '--keysize' ,'-k', nargs='*', type=int, default=[4]   , help="key sizes (4)")
	argp.add_argument( '--payload' ,'-p', nargs='*', type=int, default=[8]   , help="value sizes (8)")
	argp.add_argument( '--verbose' ,'-v', action='count'     , default=0     , help="Verbose (false)")
	args = argp.parse_args()

	debug = args.verbose

	i = 0
	for maxsize in args.maxsize:
		for keysize in args.keysize:
			for payload in args.payload:
				for level in args.level:
					sizetest(
						maxsize  = maxsize,
						keysize  = keysize,
						payload  = payload,
						level    = level,
						noheader = i
					)
					i += 1
