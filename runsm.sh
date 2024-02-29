#!/bin/sh
java -cp sm2.jar:lib/* au.edu.unimelb.services.ServiceProvider SM2 $1 ./models/$2 0.05
