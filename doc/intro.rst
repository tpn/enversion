.. intro_toplevel:

============
Introduction
============

.. _intro:

What is Enversion, and why would I want to use it?
==================================================

Enversion is a framework that sits in front of Subversion and analyzes
incoming commits, blocking those that don't meet certain criteria.

What does it do?
================
It currently blocks 87 different types of commits.  A lot of these commits are
common in the enterprise and can screw up things.

Why would I want to use it?
===========================
To improve the quality of your Subversion repository.

How does it work?
=================
Enversion is written in Python.  It ships with a command line tool called
`evnadmin`.  This tool is used to administer Enversion.

Can open source projects use it?
================================
Yes!  Although it was written specifically for enterprise users of Subversion,
there is no reason it couldn't be used on open source projects.

Is it free?
===========
Yes, after much deliberation, I decided to release Enversion as an open source
project.  It is licensed under the same terms as Subversion; i.e. the Apache
2.0 License.

Is commercial support available?
================================
Yes!  In fact, I made the decision to release Enversion as open source on the
basis that I would also offer annual commercial support and maintenance
contracts to my enterprise clients.

Who is behind it?
=================
Trent Nelson, founder of Snakebite, Inc.  Freelance consultant.

What was the motivation for developing it?
==========================================
Experience.

.. vim:set ts=8 sw=4 sts=4 tw=78 et:
