/* Deliberately unsafe fixture. Never compile or execute. */
#include <string.h>
void unsafe(const char *input) { char buffer[8]; strcpy(buffer, input); }
