
			   Paralogy Browser
			written by Nick Stoler

################################################################################


		Overview:

This application allows a site visitor to search for an E. coli gene by name, then see the genes similar in sequence to their gene of interest. Then because the similar genes are hyperlinked, the user can browse to the gene pages of the similar sequences and see their similar sequences.
On the administrator side, the application comes with a perl script which will take a multi-sequence protein FASTA file as input and fill a database with the results of a multiway BLAST search on the input sequences.



		The flow of the application:

	Performing the BLAST and filling the database (scripts in "multiblast" directory):
multiBlast.pl		performs FASTA to BLAST DB conversion, performs BLAST, fills database
  extractFasta.pm	called by multiBlast.pl

	Path of a user search:
pbsearch.html		Start page: User enters gene search term
search_results.cgi	finds matching entries, prints search results
  search_results.tmpl	used by search_results.cgi to print results HTML page
similarities.cgi	when a user clicks on a result, this prints the "similar sequences" page
  similarities.tmpl	used by similarities.cgi to print "similar sequences" HTML page
  css/style.css		styles all three pages, especially similarities.tmpl
  js/script.js		sizes E-value meters on similarities.tmpl page (see "E-value bars" below)


  
		Administrator Instructions:

Perl modules required: DBI, CGI, HTML::Template, Config::IniFiles

First the administrator must set up a MySQL database for the application, including a "sequences" and a "hits" table. The MySQL create statements are provided in mysqlCreate.txt. Then she must fill a file named "dbi_config.ini" (in the main directory) with her database connection information, in the following format:
[Connection]
user=(username)
pass=(password)
host=(MySQL host)
database=(database to use)

Then the administrator must install the NCBI legacy C toolkit BLAST applications. Finally, she  just needs to run multiBlast.pl on her FASTA file, with the FASTA file given as the first command line argument:
$ ./multiBlast.pl e_coli_k12_dh10b.faa
Then multiBlast.pl will convert the FASTA file to a BLAST database using formatdb, add information on each sequence to the MySQL "sequences" table, perform a multiway blastall search comparing every sequence to every other sequence, and finally fill the MySQL "hits" table with the results.

At this point the web application should function.

The application will work with any multi-sequence protein FASTA file, not restricted to just E. coli (or even a genome dataset). The only real considerations when using it for another dataset are editing the HTML templates to reflect the sequence set chosen.
Future versions should (ideally) make this a more automatic process.



		Behind the Scenes:

multiBlast.pl simply uses the "system" command to use formatdb: "formatdb -p T -i $faafile", creating a BLAST database out of the FASTA file.
Then it calls the main subroutine of the supplied extractFasta.pm module to parse the FASTA file and fill the "sequences" table of the database with general information on the contained sequences. extractFasta.pm uses a once-through loop to parse the lines in the FASTA file. It also parses the sequence definition lines to extract the sequence identifiers and descriptions. If the definition lines are in the correct format, it is also able to parse the sequence identifiers to extract the database and sequence ID information (i.e. it is able to understand "gi|170082747" or "ref|YP_001732067.1|").
Then multiBlast.pl again uses the "system" command to make blastall perform a BLAST search on the newly created BLAST database, using the FASTA file as the query. The results are in tabulated, tab-delimited format, and are written to a temporary file.
Then it reads through the temporary file, adding each BLAST hit to the MySQL "hits" table (though first it filters out self-hits).

When a user submits a search through the form on the pbsearch.html start page, the query is send to search_results.cgi in an HTTP POST. Then search_results.cgi connects to the database and finds all entries in the "sequences" table containing the literal (but case-insensitive) query in the description field. Then it prints the matches in an HTML page using HTML::Template and the search_results.tmpl template.
The hyperlink to each result is encoded as an HTTP GET request to similarities.cgi, with the sequence identifier in the query string. When similarities.cgi receives the request, it searches the MySQL "hits" table for any BLAST results where the selected gene was the query. It selects certain information from each BLAST result and passes the data to the similarities.tmpl template. Then it prints the resulting HTML page.
For every result on the similarities page, the identifier is hyperlinked to its own similarities page. The link uses the same GET request that is present on the search_results page. That is what allows the user to browse endlessly among the similar sequences.

E-value bars:
The similarities page uses a special visualization to represent the strength of each BLAST hit, making it easy to see at a glance the spread of the similar sequences. The visualization consists of a bar whose length is proportional to the exponent of the hit's E-value.
The bars are created with HTML5 custom data attributes and JavaScript. The template contains a (nearly) empty <section> element for each hit. The css/style.css stylesheet turns these into solid, colored rectangular bars. When filling the template, similarities.cgi calculates a pixel width for each bar based on the logarithm of each result's E-value. When it fills the template, it sets the "data-e-bar-width" attribute of the <section> elements to be their intended width. Then a script in js/scripts.js reads the attribute value and adjusts the element's pixel width to that value. Without JavaScript, the bars remain a simply decorative element, all of equal length.