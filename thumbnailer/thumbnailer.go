package main

import (
	"flag"
	"fmt"
	"gopkg.in/gographics/imagick.v2/imagick"
	"io/ioutil"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
)

var suffixes = map[string]bool{
	".jpg": true,
	".gif": true,
	".png": true,
}

var sizes = []uint{3840, 1920, 800}

var logger *log.Logger

func setupSignalHandler(done chan struct{}) {
	// setup a signal handler
	signals := make(chan os.Signal, 1)

	go func() {
		for {
			select {
			case <-signals:
				logger.Println("signal caught! ")
				close(done)
			case <-done:
				return
			}
		}
	}()

	signal.Notify(signals, os.Interrupt)
}

type result struct {
	path string
	file string
	size uint
}

func walkFiles(root string, recurse uint8, paths chan *result, done <-chan struct{}) {

	logger.Println("scan dir ", root)
	files, err := ioutil.ReadDir(root)
	if err != nil {
		log.Fatal(err)
	}

	var subDirs []string

	for _, file := range files {
		if file.Mode().IsDir() {
			// skip resize directories
			if strings.HasPrefix(file.Name(), "resize_") == false {
				subDirs = append(subDirs, file.Name())
			}
			continue
		}

		// see if this is a file we are interested in
		if _, ok := suffixes[strings.ToLower(filepath.Ext(file.Name()))]; !ok {
			//logger.Println("skipping " + file.Name())
			continue
		}

		for _, size := range sizes {
			select {
			case paths <- &result{root, file.Name(), size}:
			case <-done:
				break
			}
		}
	}

	if recurse > 0 {
		for _, subDir := range subDirs {
			select {
			case <-done:
				break
			default:
				walkFiles(root+"/"+subDir, recurse+1, paths, done)
			}
		}
	}

	if recurse <= 1 {
		close(paths)
	}
}

// take a path and a largest size dimention, resize image
func resizeImage(entry *result) bool {
	inputFile := fmt.Sprintf("%s/%s", entry.path, entry.file)
	outputDir := fmt.Sprintf("%s/resize_%d", entry.path, entry.size)
	outputFile := fmt.Sprintf("%s/%s", outputDir, entry.file)

	//logger.Println("resize dir", outputDir)

	//inputStat, _ := os.Stat(inputFile)

	// check for the output dir
	if _, statErr := os.Stat(outputDir); statErr != nil {
		if os.IsNotExist(statErr) {
			os.Mkdir(outputDir, 0775)
		} else {
			panic("expected resize dir is not a dir")
		}
	}

	// check to see if there an output file already
	if _, statErr := os.Stat(outputFile); statErr == nil {
		// TODO: check mtimes
		return true
	}

	wand := imagick.NewMagickWand()
	defer wand.Destroy()

	if err := wand.ReadImage(inputFile); err != nil {
		panic(err)
	}

	var resizeWidth, resizeHeight uint

	sizeWidth := wand.GetImageWidth()
	sizeHeight := wand.GetImageHeight()

	if sizeHeight > sizeWidth {
		resizeHeight = entry.size
		resizeWidth = sizeWidth * resizeHeight / sizeHeight
	} else {
		resizeWidth = entry.size
		resizeHeight = sizeHeight * resizeWidth / sizeWidth
	}

	if sizeWidth < resizeWidth || sizeHeight < resizeHeight {
		log.Println("skipping resize, larger then original", inputFile)
		return false
	}

	if err := wand.ResizeImage(resizeWidth, resizeHeight, imagick.FILTER_LANCZOS, 1); err != nil {
		panic(err)
	}

	if err := wand.SetImageCompressionQuality(95); err != nil {
		panic(err)
	}

	if err := wand.WriteImage(outputFile); err != nil {
		panic(err)
	}

	return true
}

func runWorkers(workerCount int, paths <-chan *result, results chan *result, done <-chan struct{}) {
	var wg sync.WaitGroup
	wg.Add(workerCount)
	for i := 1; i <= workerCount; i++ {
		go func(i int) {
			logger.Println("starting worker", i)
			defer wg.Done()

			for entry := range paths {
				resizeImage(entry)
				select {
				case <-done:
					break
				case results <- entry:
				}
			}
		}(i)
	}
	go func() {
		wg.Wait()
		// everything should be done at this point, clean itup.
		close(results)
	}()
}

func min(x, y int) int {
	if x < y {
		return x
	}
	return y
}

func main() {
	// initalize imagemagick
	imagick.Initialize()
	defer imagick.Terminate()

	recurseFlag := flag.Bool("recurse", false, "recurse subdirs")

	workersFlag := flag.Int("workers", 2, "number of workers")

	dataDirFlag := flag.String("dir", ".", "directory to work against")

	verboseFlag := flag.Bool("verbose", false, "verbose output")

	flag.Parse()

	// set up logger
	out := ioutil.Discard
	if *verboseFlag {
		out = os.Stdout
	}

	logger = log.New(out, "[thumbnailer] ", log.LUTC|log.LstdFlags)

	// resolve the directory
	dataDir, _ := filepath.Abs(*dataDirFlag)
	// then duck out to /tmp
	_ = os.Chdir("/tmp")

	recurseInt := uint8(0)
	if *recurseFlag {
		recurseInt = 1
	}

	// so image magick does not like having 8 or more threads poking around
	// runs out cache resources, even with plenty of room. :/

	workersInt := int(*workersFlag)

	// control channels
	paths := make(chan *result)
	results := make(chan *result)
	done := make(chan struct{})

	setupSignalHandler(done)

	go runWorkers(workersInt, paths, results, done)
	go walkFiles(dataDir, recurseInt, paths, done)

	for r := range results {
		logger.Println("completed", r.file, r.size)
	}

	logger.Println("done!")
}
