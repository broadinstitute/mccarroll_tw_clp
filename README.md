# Command-line tools for launching McCarroll Lab pipelines in Seqera cloud
## Installation
1. Install `tw` command-line tool using [these instructions](https://github.com/seqeralabs/tower-cli/blob/master/README.md).  
   Note that you need to create a tower access token and export it into your environment.  It is recommended
   that you put the export command in your shell startup script, e.g. ~/.bash_login.  Note that the access token
   is a secret you should protect, so protect your shell startup script, e.g. `chmod go-rw ~/.bash_login`.
2. Install uv if you don't have it already.  See 
   [Installing uv](https://docs.astral.sh/uv/getting-started/installation/#installing-uv).
3. Run one of the command-line tools, e.g.
```
uvx --from 'https://git@github.com/broadinstitute/mccarroll_tw_clp.git' launchSnRna -h
```