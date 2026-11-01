```
=======================================================
   EVALUATING REACTIVE EXPERIMENT RUN (FinalExp002)
=======================================================
Fault Injected At : 2026-11-01 19:11:02 (1793513462)
Evaluation Window : 120s (until 1793513582)

[Q2: Detection Speed]
 - Circuit Breaker OPEN at: 2026-11-01 19:11:10
 - MTTD (Mean Time to Detect / Trip): 8.00 seconds
[*] Parsing JMeter file: /Users/thisguycode/20242823/901/901-data-collection/evaluations/finalexp002-output/Reactive-FinalExp002-20261101-190902.csv...

[Q1: Client Failure Impact]
 - Total Requests Sent   : 4365
 - Failed Requests        : 3275 (75.03%)
 - Mean Client Latency   : 43.08 ms
 - P95 Client Latency    : 25.00 ms
 - Max Client Latency    : 1018.00 ms
 - Error Code Breakdown  : {503: 3275}

[Q3: Cascading Failure Prevention]
 - Order Service Peak Active Requests : 24.0 concurrent
 - Order Service Peak Live Threads     : 132.0
 - Gateway Peak Active Requests        : 0 concurrent

=======================================================
```

```
=======================================================
   EVALUATING PROACTIVE EXPERIMENT RUN (FinalExp002)
=======================================================
Fault Injected At : 2026-11-01 19:30:24 (1793514624)
Evaluation Window : 120s (until 1793514744)

[Q2: Detection Speed]
 - Circuit Breaker OPEN at: 2026-11-01 19:30:30
 - MTTD (Mean Time to Detect / Trip): 6.00 seconds
[*] Parsing JMeter file: /Users/thisguycode/20242823/901/901-data-collection/evaluations/finalexp002-output/Proactive-FinalExp002-20261101-192824.csv...

[Q1: Client Failure Impact]
 - Total Requests Sent   : 4411
 - Failed Requests        : 3353 (76.01%)
 - Mean Client Latency   : 41.09 ms
 - P95 Client Latency    : 19.00 ms
 - Max Client Latency    : 1017.00 ms
 - Error Code Breakdown  : {503: 3353}

[Q3: Cascading Failure Prevention]
 - Order Service Peak Active Requests : 29.0 concurrent
 - Order Service Peak Live Threads     : 132.0
 - Gateway Peak Active Requests        : 0 concurrent

=======================================================
```