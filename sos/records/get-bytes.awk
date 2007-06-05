$1 !~ /^NOT_REAL:$/ { bytes += $2 }
END {
	printf ("number of bytes %d\n", bytes);
}

