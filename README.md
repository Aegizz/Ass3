You will require some large text files for this assignment. Consider using resources like the Gutenberg Project (https://www.gutenberg.org) to obtain such files. Download plain text format books (UTF-8) and save them locally for later use.
To send these text files to your program, consider utilising the netcat tool (nc).  For instance, to transmit a text file to your server, you may use the following command:
```
nc localhost 1234 -i <delay> < file.txt
```
Ensure that the first line of each text file contains the title of the respective book.   This makes your program later easier, as you can grasp a book identifier easily from the incoming data stream. 
