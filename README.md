# HTTP-Download-Accelerator
A downloader built on raw sockets that splits a single file across parallel HTTP range requests, pulls the chunks concurrently, and stitches them back together in order. Handles servers that refuse range requests by falling back to a plain sequential download.
