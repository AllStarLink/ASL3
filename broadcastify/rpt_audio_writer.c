/* rpt_audio_writer.c
 * Build: gcc -O2 -Wall -o rpt_audio_writer rpt_audio_writer.c
 * Usage: rpt_audio_writer <fifo_path>
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define CHUNK 320

int main(int argc, char *argv[]) {
  if (argc != 2) {
    fprintf(stderr, "Usage: %s <fifo_path>\n", argv[0]);
    return 1;
  }

  const char *fifo_path = argv[1];

  /* Create the FIFO if it doesn't exist. If it exists as a FIFO, fine.
   * If it exists as something else (regular file, socket), bail out. */
  if (mkfifo(fifo_path, 0660) < 0) {
    if (errno != EEXIST) {
      fprintf(stderr, "mkfifo(%s): %s\n", fifo_path, strerror(errno));
      return 1;
    }
    struct stat st;
    if (stat(fifo_path, &st) < 0) {
      fprintf(stderr, "stat(%s): %s\n", fifo_path, strerror(errno));
      return 1;
    }
    if (!S_ISFIFO(st.st_mode)) {
      fprintf(stderr, "%s exists but is not a FIFO\n", fifo_path);
      return 1;
    }
  }

  /* Ignore SIGPIPE; we handle EPIPE on write() ourselves */
  signal(SIGPIPE, SIG_IGN);

  unsigned char buf[CHUNK];
  int fifo_fd = -1;

  for (;;) {
    ssize_t n = read(STDIN_FILENO, buf, CHUNK);
    if (n == 0)
      break; /* stdin closed */
    if (n < 0) {
      if (errno == EINTR)
        continue;
      break;
    }

    if (fifo_fd < 0) {
      fifo_fd = open(fifo_path, O_WRONLY | O_NONBLOCK);
      if (fifo_fd < 0)
        continue; /* no reader, drop */
    }

    ssize_t w = write(fifo_fd, buf, n);
    if (w < 0) {
      if (errno == EAGAIN) {
        continue; /* reader slow, drop chunk */
      }
      if (errno == EPIPE || errno == EBADF) {
        close(fifo_fd);
        fifo_fd = -1;
        continue;
      }
      break;
    }
  }

  if (fifo_fd >= 0)
    close(fifo_fd);
  return 0;
}
