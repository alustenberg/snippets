#!/bin/sh
CMD=$(readlink -e $0)
export GOPATH=$(dirname $CMD)
echo gopath set to $GOPATH

go get -v gopkg.in/gographics/imagick.v2/imagick &&
gofmt -w thumbnailer.go &&
go build -o thumbnail &&
find . -iname \*.go -print0 | xargs -0 ctags