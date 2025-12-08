client read --> leader or slave 
client write --> leader only --> relicate it to any slaves 

this leader replication goes to with messages brokers ( Kafka ...)

replication --> by force to be one ( asynchro or synchro ) 
asynchro:
lose data if the
leader fails


What do we do we want better alternative --> tada chain replcation 


we need to make sure that the write is durabale 


consistency of replication and consensus OUUUUU

in this lab ...most common used practice 


leader failures means we need new leader  (timeout)
if it is asynchro and we want to change the leader the new leader doesnt get all the data from the new leader 
some systems have a mechanism to shut down one
node if two leaders are detected.ii However, if this mechanism is not carefully
designed, you can end up with both nodes being shut down

log structured storage ( using SSTables and LSM Trees )
B-trees 


leader and a follower 
replication logs --->  Write-ahead log (WAL) shipping
                      Logical (row-based) log replication 
                      Problems with Replication Lag


                      




