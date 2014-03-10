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

r_node * r_nodes;
r_edge * r_edges;
IDX node_count = 0;

/* util functions */
int  readData();
int  iterWildcards(string);
void checkWord(string);
void chomp(string &);
void resetFound();

IDX findSlot(IDX, char);
IDX claimNode(char);


int main()
{ 
	readData();
	cout << "ready" << endl << flush;
	
	string line;
	while(getline(cin,line)){ 
		chomp(line);
		if(line == "done"){ 
			cout << "done" << endl << flush;
		} else if(line == "flush") { 
			resetFound();
			cout << "flush" << endl << flush;
		} else { 
			iterWildcards(line);
			// checkWord(line);
		}
	}
}

/* sluuuuurrrppp */
int readData(){ 
	fstream file(DATA_FILE, ios::in | ios::binary);
	
	r_header header;
	file.read((char*) &header, sizeof(r_header));
	
	node_count = header.node_count;
	r_nodes = new r_node[ header.node_count ];
	r_edges = new r_edge[ header.edge_count ];

	file.read((char*) r_nodes, header.node_count * sizeof(r_node) );
	file.read((char*) r_edges, header.edge_count * sizeof(r_edge) );

	file.close();
	return 0;
}

int iterWildcards(string line) { 
	//cerr << "checking " << line << endl << flush;
	string::size_type idx = line.find("_", 0 );
	if( idx == string::npos ) { 
		/* no wildcards, straight check */
		checkWord(line);
	} else { 
		/* ugh.. wildcards.. */
		for(char w = 'A'; w <= 'Z'; w++) { 
			/* i know concats are not the fastest way, but im not THAT anal about performance */
			string test  = line.substr(0,idx);
			test += w;
			test += line.substr(idx + 1, line.length() - idx);
			iterWildcards(test);
		}
	}
}

/* walk the tree and split out any matching words along the way */
void checkWord(string word){
	IDX n = 0;
	for(int i = 0; i < word.length()  ; i ++){ 
		char c = word[i];
		n = findSlot(n,c);
		if(n == 0 ){ 
			return;
		} 
		if (r_nodes[n].eow && ( ! r_nodes[n].found ) ){ 
			cout << word.substr(0,i+1) << endl;
			r_nodes[n].found = true;  /* cut down the common repeated chatter */
		}
	}
	cout << flush;
	return;
}

/* util functions */

void chomp(string &line){ 
	line.erase(remove_if(line.begin(), line.end(), ::isspace), line.end());
}

void resetFound(){ 
	for(IDX i = 0; i < node_count ; i ++){
		if(r_nodes[i].found){
			r_nodes[i].found = true;
		}
	}
}


IDX findSlot(IDX node, char next) { 
	r_edge *i_edge = &( r_edges[ r_nodes[node].edges ] );
	// cerr << "seek " << next << " from " << node << " vs " << r_nodes[node].edges << endl << flush;

	while(i_edge -> t) { 
		//cerr << "v '" << i_edge -> t << "' " << (int) i_edge -> t << " -> " << i_edge -> node << endl << flush;
		if(i_edge -> t == next) { 
			//cerr << "found it" << endl;
			return i_edge -> node;
		}
		i_edge ++;
	}
	return 0;
}
