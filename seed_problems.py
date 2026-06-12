"""Seed problem list for dsa_tracker_mcp.

This module is intentionally independent of the server: it contains only the
problem list and a couple of pure helper functions. To track a different list
(Blind 75, Grind 75, your own), replace SEED_PROBLEMS with your own
(name, category, difficulty) tuples — the server seeds the database from
whatever this module exports, in list order.

The list below is the NeetCode 150 in its standard category order.
"""

import re
from typing import Iterator, TypedDict

LEETCODE_BASE_URL = "https://leetcode.com/problems"


class SeedProblem(TypedDict):
    """A single problem row, ready to insert into the `problems` table."""

    name: str
    category: str
    difficulty: str
    leetcode_url: str
    order_index: int


def slugify(name: str) -> str:
    """Convert a problem name to a LeetCode URL slug.

    Lowercase, strip punctuation, collapse whitespace to hyphens.
    e.g. "Pow(x, n)" -> "powx-n", "3Sum" -> "3sum".
    """
    slug = re.sub(r"[^\w\s]", "", name.lower())
    return re.sub(r"\s+", "-", slug.strip())


def leetcode_url(name: str) -> str:
    """Build the LeetCode problem URL for a problem name."""
    return f"{LEETCODE_BASE_URL}/{slugify(name)}/"


# (name, category, difficulty) — order here defines order_index.
SEED_PROBLEMS: list[tuple[str, str, str]] = [
    # Arrays & Hashing (9)
    ("Contains Duplicate", "Arrays & Hashing", "Easy"),
    ("Valid Anagram", "Arrays & Hashing", "Easy"),
    ("Two Sum", "Arrays & Hashing", "Easy"),
    ("Group Anagrams", "Arrays & Hashing", "Medium"),
    ("Top K Frequent Elements", "Arrays & Hashing", "Medium"),
    ("Encode and Decode Strings", "Arrays & Hashing", "Medium"),
    ("Product of Array Except Self", "Arrays & Hashing", "Medium"),
    ("Valid Sudoku", "Arrays & Hashing", "Medium"),
    ("Longest Consecutive Sequence", "Arrays & Hashing", "Medium"),
    # Two Pointers (5)
    ("Valid Palindrome", "Two Pointers", "Easy"),
    ("Two Sum II Input Array Is Sorted", "Two Pointers", "Medium"),
    ("3Sum", "Two Pointers", "Medium"),
    ("Container With Most Water", "Two Pointers", "Medium"),
    ("Trapping Rain Water", "Two Pointers", "Hard"),
    # Sliding Window (6)
    ("Best Time to Buy and Sell Stock", "Sliding Window", "Easy"),
    ("Longest Substring Without Repeating Characters", "Sliding Window", "Medium"),
    ("Longest Repeating Character Replacement", "Sliding Window", "Medium"),
    ("Permutation in String", "Sliding Window", "Medium"),
    ("Minimum Window Substring", "Sliding Window", "Hard"),
    ("Sliding Window Maximum", "Sliding Window", "Hard"),
    # Stack (7)
    ("Valid Parentheses", "Stack", "Easy"),
    ("Min Stack", "Stack", "Medium"),
    ("Evaluate Reverse Polish Notation", "Stack", "Medium"),
    ("Generate Parentheses", "Stack", "Medium"),
    ("Daily Temperatures", "Stack", "Medium"),
    ("Car Fleet", "Stack", "Medium"),
    ("Largest Rectangle in Histogram", "Stack", "Hard"),
    # Binary Search (7)
    ("Binary Search", "Binary Search", "Easy"),
    ("Search a 2D Matrix", "Binary Search", "Medium"),
    ("Koko Eating Bananas", "Binary Search", "Medium"),
    ("Find Minimum in Rotated Sorted Array", "Binary Search", "Medium"),
    ("Search in Rotated Sorted Array", "Binary Search", "Medium"),
    ("Time Based Key Value Store", "Binary Search", "Medium"),
    ("Median of Two Sorted Arrays", "Binary Search", "Hard"),
    # Linked List (11)
    ("Reverse Linked List", "Linked List", "Easy"),
    ("Merge Two Sorted Lists", "Linked List", "Easy"),
    ("Linked List Cycle", "Linked List", "Easy"),
    ("Reorder List", "Linked List", "Medium"),
    ("Remove Nth Node From End of List", "Linked List", "Medium"),
    ("Copy List With Random Pointer", "Linked List", "Medium"),
    ("Add Two Numbers", "Linked List", "Medium"),
    ("Find the Duplicate Number", "Linked List", "Medium"),
    ("LRU Cache", "Linked List", "Medium"),
    ("Merge K Sorted Lists", "Linked List", "Hard"),
    ("Reverse Nodes in K Group", "Linked List", "Hard"),
    # Trees (15)
    ("Invert Binary Tree", "Trees", "Easy"),
    ("Maximum Depth of Binary Tree", "Trees", "Easy"),
    ("Diameter of Binary Tree", "Trees", "Easy"),
    ("Balanced Binary Tree", "Trees", "Easy"),
    ("Same Tree", "Trees", "Easy"),
    ("Subtree of Another Tree", "Trees", "Easy"),
    ("Lowest Common Ancestor of a Binary Search Tree", "Trees", "Medium"),
    ("Binary Tree Level Order Traversal", "Trees", "Medium"),
    ("Binary Tree Right Side View", "Trees", "Medium"),
    ("Count Good Nodes in Binary Tree", "Trees", "Medium"),
    ("Validate Binary Search Tree", "Trees", "Medium"),
    ("Kth Smallest Element in a BST", "Trees", "Medium"),
    ("Construct Binary Tree from Preorder and Inorder Traversal", "Trees", "Medium"),
    ("Binary Tree Maximum Path Sum", "Trees", "Hard"),
    ("Serialize and Deserialize Binary Tree", "Trees", "Hard"),
    # Heap / Priority Queue (7)
    ("Kth Largest Element in a Stream", "Heap / Priority Queue", "Easy"),
    ("Last Stone Weight", "Heap / Priority Queue", "Easy"),
    ("K Closest Points to Origin", "Heap / Priority Queue", "Medium"),
    ("Kth Largest Element in an Array", "Heap / Priority Queue", "Medium"),
    ("Task Scheduler", "Heap / Priority Queue", "Medium"),
    ("Design Twitter", "Heap / Priority Queue", "Medium"),
    ("Find Median From Data Stream", "Heap / Priority Queue", "Hard"),
    # Backtracking (9)
    ("Subsets", "Backtracking", "Medium"),
    ("Combination Sum", "Backtracking", "Medium"),
    ("Permutations", "Backtracking", "Medium"),
    ("Subsets II", "Backtracking", "Medium"),
    ("Combination Sum II", "Backtracking", "Medium"),
    ("Word Search", "Backtracking", "Medium"),
    ("Palindrome Partitioning", "Backtracking", "Medium"),
    ("Letter Combinations of a Phone Number", "Backtracking", "Medium"),
    ("N Queens", "Backtracking", "Hard"),
    # Trie (3)
    ("Implement Trie (Prefix Tree)", "Trie", "Medium"),
    ("Design Add and Search Words Data Structure", "Trie", "Medium"),
    ("Word Search II", "Trie", "Hard"),
    # Graphs (13)
    ("Number of Islands", "Graphs", "Medium"),
    ("Clone Graph", "Graphs", "Medium"),
    ("Max Area of Island", "Graphs", "Medium"),
    ("Pacific Atlantic Water Flow", "Graphs", "Medium"),
    ("Surrounded Regions", "Graphs", "Medium"),
    ("Rotting Oranges", "Graphs", "Medium"),
    ("Walls and Gates", "Graphs", "Medium"),
    ("Course Schedule", "Graphs", "Medium"),
    ("Course Schedule II", "Graphs", "Medium"),
    ("Redundant Connection", "Graphs", "Medium"),
    ("Number of Connected Components in an Undirected Graph", "Graphs", "Medium"),
    ("Graph Valid Tree", "Graphs", "Medium"),
    ("Word Ladder", "Graphs", "Hard"),
    # Advanced Graphs (6)
    ("Reconstruct Itinerary", "Advanced Graphs", "Hard"),
    ("Min Cost to Connect All Points", "Advanced Graphs", "Medium"),
    ("Network Delay Time", "Advanced Graphs", "Medium"),
    ("Swim in Rising Water", "Advanced Graphs", "Hard"),
    ("Alien Dictionary", "Advanced Graphs", "Hard"),
    ("Cheapest Flights Within K Stops", "Advanced Graphs", "Medium"),
    # 1-D DP (12)
    ("Climbing Stairs", "1-D DP", "Easy"),
    ("Min Cost Climbing Stairs", "1-D DP", "Easy"),
    ("House Robber", "1-D DP", "Medium"),
    ("House Robber II", "1-D DP", "Medium"),
    ("Longest Palindromic Substring", "1-D DP", "Medium"),
    ("Palindromic Substrings", "1-D DP", "Medium"),
    ("Decode Ways", "1-D DP", "Medium"),
    ("Coin Change", "1-D DP", "Medium"),
    ("Maximum Product Subarray", "1-D DP", "Medium"),
    ("Word Break", "1-D DP", "Medium"),
    ("Longest Increasing Subsequence", "1-D DP", "Medium"),
    ("Partition Equal Subset Sum", "1-D DP", "Medium"),
    # 2-D DP (11)
    ("Unique Paths", "2-D DP", "Medium"),
    ("Longest Common Subsequence", "2-D DP", "Medium"),
    ("Best Time to Buy and Sell Stock With Cooldown", "2-D DP", "Medium"),
    ("Coin Change II", "2-D DP", "Medium"),
    ("Target Sum", "2-D DP", "Medium"),
    ("Interleaving String", "2-D DP", "Medium"),
    ("Longest Increasing Path in a Matrix", "2-D DP", "Hard"),
    ("Distinct Subsequences", "2-D DP", "Hard"),
    ("Edit Distance", "2-D DP", "Medium"),
    ("Burst Balloons", "2-D DP", "Hard"),
    ("Regular Expression Matching", "2-D DP", "Hard"),
    # Greedy (8)
    ("Maximum Subarray", "Greedy", "Medium"),
    ("Jump Game", "Greedy", "Medium"),
    ("Jump Game II", "Greedy", "Medium"),
    ("Gas Station", "Greedy", "Medium"),
    ("Hand of Straights", "Greedy", "Medium"),
    ("Merge Triplets to Form Target Triplet", "Greedy", "Medium"),
    ("Partition Labels", "Greedy", "Medium"),
    ("Valid Parenthesis String", "Greedy", "Medium"),
    # Intervals (6)
    ("Insert Interval", "Intervals", "Medium"),
    ("Merge Intervals", "Intervals", "Medium"),
    ("Non Overlapping Intervals", "Intervals", "Medium"),
    ("Meeting Rooms", "Intervals", "Easy"),
    ("Meeting Rooms II", "Intervals", "Medium"),
    ("Minimum Interval to Include Each Query", "Intervals", "Hard"),
    # Math & Geometry (8)
    ("Rotate Image", "Math & Geometry", "Medium"),
    ("Spiral Matrix", "Math & Geometry", "Medium"),
    ("Set Matrix Zeroes", "Math & Geometry", "Medium"),
    ("Happy Number", "Math & Geometry", "Easy"),
    ("Plus One", "Math & Geometry", "Easy"),
    ("Pow(x, n)", "Math & Geometry", "Medium"),
    ("Multiply Strings", "Math & Geometry", "Medium"),
    ("Detect Squares", "Math & Geometry", "Medium"),
    # Bit Manipulation (7)
    ("Single Number", "Bit Manipulation", "Easy"),
    ("Number of 1 Bits", "Bit Manipulation", "Easy"),
    ("Counting Bits", "Bit Manipulation", "Easy"),
    ("Reverse Bits", "Bit Manipulation", "Easy"),
    ("Missing Number", "Bit Manipulation", "Easy"),
    ("Sum of Two Integers", "Bit Manipulation", "Medium"),
    ("Reverse Integer", "Bit Manipulation", "Medium"),
]


def iter_seed_problems() -> Iterator[SeedProblem]:
    """Yield seed problems as full rows with order_index and leetcode_url."""
    for index, (name, category, difficulty) in enumerate(SEED_PROBLEMS, start=1):
        yield SeedProblem(
            name=name,
            category=category,
            difficulty=difficulty,
            leetcode_url=leetcode_url(name),
            order_index=index,
        )


if __name__ == "__main__":
    # Quick sanity check: run `python seed_problems.py` to see the breakdown.
    from collections import Counter

    counts = Counter(category for _, category, _ in SEED_PROBLEMS)
    for category, count in counts.items():
        print(f"{count:3}  {category}")
    print(f"{len(SEED_PROBLEMS):3}  TOTAL")
    sample = next(iter_seed_problems())
    print(f"\nSample URL: {sample['name']} -> {sample['leetcode_url']}")
