/*trie.c, 

read a bunch of words from a file
read a validation word from stdin, return possible matches on stdout
read 'done' from stdin and echo 'done' to stdout. 

*/
#include <algorithm> // for chomp. why chomp isnt in <string> is beyond me.
#include <exception>
#include <fstream>
#include <iostream>

#include "s_common.h"
using namespace std;

p_node nodes[MAX_NODES];
long next_unused = 0; 

int max_slots = 0;
long total_slots = 0;

/* util functions */
int  readWords();
int  writeData();

int  addWord(string);
int  checkWord(string);
void chomp(string &);

long getSlot(long, char);
long claimNode(char);


int main()
{ 
	readWords();
	writeData();

	cout << "ok" << endl;
	return 0;
}

int readWords(){ 
	fstream file(WORD_FILE, fstream::in);
	if(not file.is_open()){ 
		cout << "cannot open file" << endl;
		throw;
	}

	string line;
	while(file.good()){ 
		getline(file, line);
		chomp(line);
		if(line.length() > 0) { 
			addWord(line);
		}
	}
	//cout << "file read" << endl;
	file.close();
}

int addWord(string word){ 
	// cout << "adding word " << word << endl;
	long n = 0;
	n = 0;
	for(int i = 0; i < word.length(); i ++) { 
		char c = word[i];
		n = getSlot(n,c);
	}
	nodes[n].eow = true;
}


/* util functions */
/* not really a 'chomp', but a full out non word strip */
void chomp(string &line){ 
	line.erase(remove_if(line.begin(), line.end(), ::isspace), line.end());
}

/* walk the arrays and find next char, allocating if needed */
long getSlot(long start, char next) { 
	for(int i = 0; i < MAX_EDGES; i++) { 
		//cout << start << "," << next << "," << i << endl;
		if( nodes[start].edges[i] == 0 ) { 
		
			// end o the line, didnt find it.  snag and return
			long new_node = claimNode(next);
			nodes[start].edges[i] = new_node;

			if(i > max_slots){ 
				max_slots = i;
			}
			total_slots ++;
			return new_node;
		} 
		if( nodes[ nodes[start].edges[i] ].c == next ) { 
			return nodes[start].edges[i]; // return where the match points at. caller doesnt care about what slot it is
		}

	}
	cout << "cannot allocate slot" << endl;
	throw;
}

long claimNode(char next){ 
	long new_node = next_unused; 
	next_unused ++;
	if(next_unused > MAX_NODES){ 
		cout << "cannot allocate node";
		throw;
	}
	
	nodes[new_node].c = next;
	nodes[new_node].eow = false;

	return new_node;
}

/* all this for a half second of startup time */
int writeData(){
	IDX p_n, o_n, o_e;
	p_n = 0; // parse node
	o_n = 0; // output node
	o_e = 0; // output edge
	
	ofstream dat(DATA_FILE, ios::out | ios::binary);
	
	r_header header;
	dat.write((char *)&header, sizeof(r_header)); // we'll come back to this later

	for(p_n = 0; p_n < next_unused; p_n ++){
		r_node o_node;
		p_node * i_node = &( nodes[p_n] );

		o_node.c     = i_node -> c;
		o_node.eow   = i_node -> eow;
		o_node.edges = o_e;

		dat.write( (char *) &o_node, sizeof(r_node));
		
		/* keep track of where it would be when we do write it out to the file */
		for(int i = 0; i < MAX_EDGES && i_node -> edges[i] != 0; i++) { 
			o_e ++;
		}	
		o_e ++; /* for null term */
	}
	
	/* and around again to write out the edges */
	o_e = 0;
	for(p_n = 0; p_n < next_unused; p_n ++){
		p_node * i_node = &( nodes[p_n] );
		
		for(int i = 0; i < MAX_EDGES && ( i_node -> edges[i] != 0); i++) { 
			r_edge o_edge;
			o_edge.node =        i_node -> edges[i];
			o_edge.t    = nodes[ i_node -> edges[i] ].c;
			dat.write( (char *)&o_edge, sizeof(r_edge) );

			o_e ++;
		}	

		r_edge null_edge;
		null_edge.node = 0;
		null_edge.t = 0;
		
		dat.write( (char *)&null_edge, sizeof(r_edge) );
		o_e ++; /* for null term */
	}

	dat.seekp(0, ios::beg); /* back to start to write out header */
	
	header.node_count = next_unused;
	header.edge_count = o_e;

	dat.write((char *)&header, sizeof(r_header) );
	dat.close();	
	return 0;
};
