/* Copyright (C) 2015-2021, Wazuh Inc.
 * Copyright (C) 2009 Trend Micro Inc.
 * All right reserved.
 *
 * This program is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public
 * License (version 2) as published by the FSF - Free Software
 * Foundation
 */

#include "shared.h"
#include "os_crypto/md5/md5_op.h"
#include "os_net/os_net.h"
#include "agentd.h"

/* Keeps hash in memory until a change is identified */
static char *g_shared_mg_file_hash = NULL;
/* Keeps the timestamp of the last notification. */
static time_t g_saved_time = 0;

/* Return the names of the files in a directory */
char *getsharedfiles()
{
    unsigned int m_size = 64;
    char *ret;
    os_md5 md5sum;

    if (OS_MD5_File(SHAREDCFG_FILE, md5sum, OS_TEXT) != 0) {
        md5sum[0] = 'x';
        md5sum[1] = '\0';
    }

    /* We control these files, max size is m_size */
    ret = (char *)calloc(m_size + 1, sizeof(char));
    if (ret) {
        snprintf(ret, m_size, "%s merged.mg\n", md5sum);
    }

    return (ret);
}

#ifndef WIN32
char *get_agent_ip()
{
    static char agent_ip[IPSIZE + 1] = { '\0' };
#if defined (__linux__) || defined (__MACH__) || defined (sun) || defined(FreeBSD) || defined(OpenBSD)
    static time_t last_update = 0;
    time_t now = time(NULL);
    int sock;
    int i;

    if ((now - last_update) < agt->main_ip_update_interval) {
        return strdup(agent_ip);
    }

    last_update = now;
    agent_ip[0] = '\0';

    for (i = SOCK_ATTEMPTS; i > 0; --i) {
        if (sock = control_check_connection(), sock >= 0) {
            if (OS_SendUnix(sock, agent_ip, IPSIZE) < 0) {
                mdebug1("Error sending msg to control socket (%d) %s", errno, strerror(errno));
                last_update = 0;
            }
            else{
                if (OS_RecvUnix(sock, IPSIZE, agent_ip) <= 0) {
                    mdebug1("Error receiving msg from control socket (%d) %s", errno, strerror(errno));
                    last_update = 0;
                    agent_ip[0] = '\0';
                }
            }

            close(sock);
            break;
        } else {
            mdebug2("Control module not yet available. Remaining attempts: %d", i - 1);
            sleep(1);
        }
    }

    if(sock < 0) {
        mdebug1("Cannot get the agent host's IP because the control module is not available: (%d) %s.", errno, strerror(errno));
        last_update = 0;
    }
#endif
    return strdup(agent_ip);
}
#endif /* !WIN32 */

/* Clear merged hash cache, to be updated in the next iteration.*/
void clear_merged_hash_cache() {
    os_free(g_shared_mg_file_hash);
}

/* Periodically send notification to server */
void run_notify()
{
    char tmp_msg[OS_MAXSTR - OS_HEADER_SIZE + 2];
    static char tmp_labels[OS_MAXSTR - OS_SIZE_2048] = { '\0' };
    os_md5 md5sum;
    time_t curr_time;
    char *agent_ip;

    tmp_msg[OS_MAXSTR - OS_HEADER_SIZE + 1] = '\0';
    curr_time = time(0);

#ifndef ONEWAY_ENABLED
    /* Check if the server has responded */
    if ((curr_time - available_server) > agt->max_time_reconnect_try) {
        /* If response is not available, set lock and wait for it */
        mwarn(SERVER_UNAV);
        os_setwait();
        w_agentd_state_update(UPDATE_STATUS, (void *) GA_STATUS_NACTIVE);

        /* Send sync message */
        start_agent(0);

        minfo(SERVER_UP);
        os_delwait();
        w_agentd_state_update(UPDATE_STATUS, (void *) GA_STATUS_ACTIVE);
    }
#endif

    /* Check if the agent has to be reconnected */
    if (agt->force_reconnect_interval && (curr_time - last_connection_time) >= agt->force_reconnect_interval) {
        /* Set lock and wait for it */
        minfo("Wazuh Agent will be reconnected because of force reconnect interval");
        os_setwait();
        w_agentd_state_update(UPDATE_STATUS, (void *) GA_STATUS_NACTIVE);

        /* Send sync message */
        start_agent(0);

        os_delwait();
        w_agentd_state_update(UPDATE_STATUS, (void *) GA_STATUS_ACTIVE);
    }

    /* Check if time has elapsed */
    if ((curr_time - g_saved_time) < agt->notify_time) {
        return;
    }
    g_saved_time = curr_time;

    mdebug1("Sending agent notification.");

    /* Send the message
     * Message is going to be the uname\n checksum file\n checksum file\n
     */

    /* Get uname */
    if (!getuname()) {
        merror(MEM_ERROR, errno, strerror(errno));
    }

    /* Format labeled data
     * Limit maximum size of the labels to avoid truncation of the keep-alive message
     */
    if (!tmp_labels[0] && labels_format(agt->labels, tmp_labels, OS_MAXSTR - OS_SIZE_2048) < 0) {
        mwarn("Too large labeled data. Not all labels will be shown in the keep-alive messages.");
    }

    /* Get shared files */
    struct stat stat_fd;
    if (!g_shared_mg_file_hash) {
        g_shared_mg_file_hash = getsharedfiles();
        if (!g_shared_mg_file_hash) {
            merror(MEM_ERROR, errno, strerror(errno));
            return;
        }
    } else if(stat(SHAREDCFG_FILE, &stat_fd) == -1 && ENOENT == errno) {
        clear_merged_hash_cache();
    }

    agent_ip = get_agent_ip();

    /* Create message */
    if(agent_ip && strcmp(agent_ip, "Err")) {
        char label_ip[60];
        snprintf(label_ip, sizeof label_ip, "#\"_agent_ip\":%s", agent_ip);
        if ((File_DateofChange(AGENTCONFIG) > 0 ) &&
                (OS_MD5_File(AGENTCONFIG, md5sum, OS_TEXT) == 0)) {
            snprintf(tmp_msg, OS_MAXSTR - OS_HEADER_SIZE, "#!-%s / %s\n%s%s%s\n",
                    getuname(), md5sum, tmp_labels, g_shared_mg_file_hash ? g_shared_mg_file_hash : "x", label_ip);
        } else {
            snprintf(tmp_msg, OS_MAXSTR - OS_HEADER_SIZE, "#!-%s\n%s%s%s\n",
                    getuname(), tmp_labels, g_shared_mg_file_hash ? g_shared_mg_file_hash : "x", label_ip);
        }
    }
    else {
        if ((File_DateofChange(AGENTCONFIG) > 0 ) &&
                (OS_MD5_File(AGENTCONFIG, md5sum, OS_TEXT) == 0)) {
            snprintf(tmp_msg, OS_MAXSTR - OS_HEADER_SIZE, "#!-%s / %s\n%s%s\n",
                    getuname(), md5sum, tmp_labels, g_shared_mg_file_hash ? g_shared_mg_file_hash : "x");
        } else {
            snprintf(tmp_msg, OS_MAXSTR - OS_HEADER_SIZE, "#!-%s\n%s%s\n",
                    getuname(), tmp_labels, g_shared_mg_file_hash ? g_shared_mg_file_hash : "x");
        }
    }
    os_free(agent_ip);

    /* Send status message */
    mdebug2("Sending keep alive: %s", tmp_msg);
    send_msg(tmp_msg, -1);

    w_agentd_state_update(UPDATE_KEEPALIVE, (void *) &curr_time);
    return;
}
