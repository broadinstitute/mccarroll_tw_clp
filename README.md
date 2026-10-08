# Command-line tools for launching McCarroll Lab pipelines in Seqera cloud
## Installation
1. [Install tw command-line tool](https://github.com/seqeralabs/tower-cli/blob/master/README.md).  
   Note that you need to create a tower access token and export it into your environment.  It is recommended
   that you put the export command in your shell startup script, e.g. ~/.bash_login.  Note that the access token
   is a secret you should protect, so protect your shell startup script, e.g. `chmod go-rw ~/.bash_login`.
2. [Install uv](https://docs.astral.sh/uv/getting-started/installation/#installing-uv) if not already installed.
3. [Install git](https://git-scm.com/install/) if  not already installed.
## Running
Run one of the command-line tools:
```
uvx --from 'https://git@github.com/broadinstitute/mccarroll_tw_clp.git' <name> -h
```
where `<name>` is one of:
- launchSnRna: launch an snRNA-seq pipeline in Seqera cloud starting with FASTQ files.
- launchSnRnaDragen: launch one or more snRNA-seq pipelines in Seqera cloud starting 
with DRAGEN output.
- launchSnRnaStage: launch an snRNA-seq pipeline in Seqera cloud starting in 
the middle of the workflow based on existing snRNA output.
- reportAndValidateSampleIndices: generate a report of sample indices and validate 
that distribution of reads between libraries is reasonably even, and that not too many 
sample indices are unknown.
