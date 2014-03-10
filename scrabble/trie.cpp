/*trie.c, 

read a bunch of words from a file
read a validation word from stdin, return possible matches on stdout
read 'done' from stdin and echo 'done' to stdout. 

*/
#include <algorithm> // for chomp. why chomp isnt in <string> is beyond me.
#include <exception>
#include <fstream>
#include <iostream>

#include <limits.h>

using namespace std;

/* from trial and error against combined wordlists */
/* TODO : parse down into a streamable format from .dmp into the array. */
#define MAX_EDGES 27 
#define MAX_NODES 900000
#define MAX_LENGTH 16

struct node { 
	char c;
	long edges[MAX_EDGES];
	bool eow; // end of word
} ;

node nodes[MAX_NODES];
long next_unused = 0; 

int max_slots = 0;
long total_slots = 0;

/* util functions */
int  readWords();
int  addWord(string);
int  checkWord(string);
void chomp(string &);

long getSlot(long, char, bool);
long claimNode(char);


int main()
{ 
	readWords();
	cout << "nodes    : " << next_unused << endl;
	cout << "slots    : " << total_slots << endl;
	cout << "max per node slots  : " << max_slots << endl;
	cout << "node size: " << sizeof(node) << endl;
	cout << "total    : " << sizeof(nodes) << endl;
	cout << "ready" << endl << flush;
	string line;
	while(getline(cin,line)){ 
		chomp(line);
		if(line == "done"){ 
			cout << "done" << endl << flush;
		} else if(line == "flush"){ 
			cout << "flush" << endl << flush;
		} else { 
			checkWord(line);
		}
	}
}

int readWords(){ 
	ifstream file;
	string line;
	file.open("words.txt");
	if(not file.is_open()){ 
		cout << "cannot open file" << endl;
		throw;
	}

	//cout << "reading file" << endl;
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
		n = getSlot(n,c,true);
	}
	nodes[n].eow = true;
}

int checkWord(string word){
	long n = 0;
	int count = 0;
	for(int i = 0; i <= word.length() ; i ++){ 
		char c = word[i];
		n = getSlot(n,c,false);
		if(n == 0 ){ 
			return false;
		}
		if (nodes[n].eow){ 
			cout << word.substr(0,i+1) << endl;
		}
	}
	cout << flush;
	return count;
}

/* util functions */

void chomp(string &line){ 
	line.erase(remove_if(line.begin(), line.end(), ::isspace), line.end());
}

long getSlot(long start, char next, bool allocate = false) { 
	for(int i = 0; i < MAX_EDGES; i++) { 
		//cout << start << "," << next << "," << i << endl;
		if( nodes[start].edges[i] == 0 ) { 
			if( not allocate) { 
				return 0;
			} 

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
	if(allocate){ 
		cout << "cannot allocate slot" << endl;
		throw;
	}
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
