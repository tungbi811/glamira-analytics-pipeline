# Shortcuts for everyday commands. Run `make` to list them.
# Override per person if needed, e.g. `make ssh ZONE=us-central1-a`.

VM   ?= glamira-vm
ZONE ?= asia-southeast1-a
IAP  := --zone=$(ZONE) --tunnel-through-iap

.DEFAULT_GOAL := help
.PHONY: help ssh tunnel vm-start vm-stop vm-status

help: ## List available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

ssh: ## Open a shell on the VM
	gcloud compute ssh $(VM) $(IAP)

tunnel: ## Forward localhost:27017 to MongoDB on the VM (Ctrl+C to close)
	@echo "Tunnel open: connect to localhost:27017. Ctrl+C to close."
	gcloud compute ssh $(VM) $(IAP) -- -N -L 27017:localhost:27017

vm-start: ## Start the VM
	gcloud compute instances start $(VM) --zone=$(ZONE)

vm-stop: ## Stop the VM (saves money; disk is kept)
	gcloud compute instances stop $(VM) --zone=$(ZONE)

vm-status: ## Show whether the VM is running
	@gcloud compute instances describe $(VM) --zone=$(ZONE) --format="value(status)"
