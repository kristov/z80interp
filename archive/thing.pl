#!/usr/bin/env perl

use strict;
use warnings;
use Data::Dumper;

my $dat = {};
while (my $l = <STDIN>) {
    chomp $l;
    my ($op, $rest) = split(/\s/, $l);
    if (!$rest) {
    }
}

my $patts = {};
for my $op (keys %{$dat}) {
    my $pat = join('|', sort {$a cmp $b} keys %{$dat->{$op}});
    $patts->{$pat}->{$op}++;
}

print Dumper($patts);
