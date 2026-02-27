package evm

import (
    "context"
    "log"
    "math/big"
    "github.com/ethereum/go-ethereum/ethclient"
    "github.com/ethereum/go-ethereum/core/types"
)

type Listener struct {
    Client       *ethclient.Client
    USDCContract string
}

func NewListener(rpcURL string, usdcContract string) (*Listener, error) {
    client, err := ethclient.Dial(rpcURL)
    if err != nil {
        return nil, err
    }
    return &Listener{Client: client, USDCContract: usdcContract}, nil
}

func (l *Listener) Start(ctx context.Context) {
    headers := make(chan *types.Header)
    sub, err := l.Client.SubscribeNewHead(ctx, headers)
    if err != nil {
        log.Fatal(err)
    }

    for {
        select {
        case <-ctx.Done():
            return
        case err := <-sub.Err():
            log.Println("subscription error:", err)
        case header := <-headers:
            l.processBlock(header.Number.Int64())
        }
    }
}

func (l *Listener) processBlock(number int64) {
    log.Printf("Processing block %d\n", number)
}
