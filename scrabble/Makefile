CCFLAGS=-g
#CCFLAGS=-O2

all: trie trie2-parse trie2-run words.dat

.cpp:
	g++ $(CCFLAGS) $< -o $@

words.dat: trie2-parse words.txt
	./trie2-parse

clean:
	rm -fv trie trie2-parse trie2-run words.dat

