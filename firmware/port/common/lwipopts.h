/* lwIP の設定（STM32 と、Linux で試す host 版の共通） */
#ifndef LWIPOPTS_H
#define LWIPOPTS_H

#define NO_SYS                  1
#define SYS_LIGHTWEIGHT_PROT    0
#define LWIP_SOCKET             0
#define LWIP_NETCONN            0
#define LWIP_RAW                0

#define MEM_ALIGNMENT           4
#define MEM_SIZE                (24 * 1024)
#define MEMP_NUM_PBUF           48
#define MEMP_NUM_UDP_PCB        6
/* WebSocket 30（BOX_MAX_CONN）+ HTTP 8 + 余裕。TIME_WAIT の分も見込む */
#define MEMP_NUM_TCP_PCB        48
#define MEMP_NUM_TCP_PCB_LISTEN 2
#define MEMP_NUM_TCP_SEG        96
#define MEMP_NUM_SYS_TIMEOUT    10
#define PBUF_POOL_SIZE          16
#define PBUF_POOL_BUFSIZE       1536

#define LWIP_ARP                1
#define ARP_TABLE_SIZE          16
#define ETHARP_SUPPORT_STATIC_ENTRIES 0
#define LWIP_ICMP               1
#define LWIP_DHCP               1
#define LWIP_AUTOIP             0
#define LWIP_IGMP               1
#define LWIP_UDP                1
#define LWIP_TCP                1
#define LWIP_IPV6               0
#define LWIP_DNS                0

#define TCP_MSS                 1460
#define TCP_SND_BUF             (4 * TCP_MSS)
#define TCP_SND_QUEUELEN        ((4 * TCP_SND_BUF) / TCP_MSS + 8)
#define TCP_WND                 (4 * TCP_MSS)
#define TCP_LISTEN_BACKLOG      1
#define LWIP_TCP_KEEPALIVE      1
#define TCP_MSL                 2000UL  /* TIME_WAIT を短くして PCB を早く空ける */

#define LWIP_NETIF_LINK_CALLBACK   1
#define LWIP_NETIF_STATUS_CALLBACK 1
#define LWIP_NETIF_HOSTNAME        1
#define LWIP_SINGLE_NETIF          1

/* Art-Net（UDP 6454）と sACN（5568）は宛先 IP を問わず受ける。2.255.255.255 や 10.255.255.255 宛てのブロードキャストと、
 * サブネットマスクが送り手と違うときのため */
#define LWIP_IP_ACCEPT_UDP_PORT(port) ((port) == PP_NTOHS(6454) || (port) == PP_NTOHS(5568))

#define LWIP_STATS              0
#define LWIP_DEBUG_TIMERNAMES   0

#ifdef ODE_HW_CHECKSUM          /* 送信のチェックサムは STM32 の MAC が入れる（受信は lwIP で確かめる） */
#define CHECKSUM_GEN_IP         0
#define CHECKSUM_GEN_UDP        0
#define CHECKSUM_GEN_TCP        0
#define CHECKSUM_GEN_ICMP       0
#endif

#endif
