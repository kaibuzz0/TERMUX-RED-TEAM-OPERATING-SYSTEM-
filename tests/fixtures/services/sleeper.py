#!/usr/bin/env python3
"""Sleeps for a given duration."""

import argparse
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("duration", type=int, default=10)
    args = parser.parse_args()
    time.sleep(args.duration)


if __name__ == "__main__":
    main()
