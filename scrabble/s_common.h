#ifndef S_COMMON
#define S_COMMON 
#include <inttypes.h>

#define IDX uint64_t
#define DATA_FILE "words.dat"
#define WORD_FILE "words.txt"

/* from trial and error against combined wordlists */
#define MAX_EDGES 32 
#define MAX_NODES 1200000
#define MAX_LENGTH 16


#include <limits.h>

/* parsing node */
struct p_node { 
	char c;
	IDX edges[MAX_EDGES];
	bool eow; // end of word
} ;

/* runtime node */
struct r_node { 
	char c; /* possibly duped now */
	bool eow;
	bool found; /* have we found this word yet in this search? */
	IDX edges; /* offset into edges tables */
};

/* runtime edge array */
struct r_edge { 
	char t; /* target char */
	IDX node; /* offset into node table */
};

/* runtime data size defs */
struct r_header { 
	IDX node_count;
	IDX edge_count;
};
#endif
