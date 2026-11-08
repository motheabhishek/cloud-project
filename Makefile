CONFIG ?= training/config.yaml

.PHONY: train
train:
	python training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)
