IMAGE ?= filefrog/dspatch
TAG   ?= latest

build:
	docker build -t $(IMAGE):$(TAG) .
push: build
	docker push $(IMAGE):$(TAG)
