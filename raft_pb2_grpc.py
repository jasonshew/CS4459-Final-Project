# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import raft_pb2 as raft__pb2


class RaftStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.AppendEntries = channel.stream_unary(
                '/raft.Raft/AppendEntries',
                request_serializer=raft__pb2.AppendEntriesMessage.SerializeToString,
                response_deserializer=raft__pb2.AppendEntriesResponse.FromString,
                )
        self.RequestVote = channel.unary_unary(
                '/raft.Raft/RequestVote',
                request_serializer=raft__pb2.RequestVoteMessage.SerializeToString,
                response_deserializer=raft__pb2.RequestVoteResponse.FromString,
                )
        self.GetLeader = channel.unary_unary(
                '/raft.Raft/GetLeader',
                request_serializer=raft__pb2.EmptyMessage.SerializeToString,
                response_deserializer=raft__pb2.GetLeaderResponse.FromString,
                )
        self.SetKeyVal = channel.unary_unary(
                '/raft.Raft/SetKeyVal',
                request_serializer=raft__pb2.SetKeyValMessage.SerializeToString,
                response_deserializer=raft__pb2.SetKeyValResponse.FromString,
                )
        self.GetVal = channel.unary_unary(
                '/raft.Raft/GetVal',
                request_serializer=raft__pb2.GetValMessage.SerializeToString,
                response_deserializer=raft__pb2.GetValResponse.FromString,
                )


class RaftServicer(object):
    """Missing associated documentation comment in .proto file."""

    def AppendEntries(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RequestVote(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetLeader(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetKeyVal(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetVal(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RaftServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'AppendEntries': grpc.stream_unary_rpc_method_handler(
                    servicer.AppendEntries,
                    request_deserializer=raft__pb2.AppendEntriesMessage.FromString,
                    response_serializer=raft__pb2.AppendEntriesResponse.SerializeToString,
            ),
            'RequestVote': grpc.unary_unary_rpc_method_handler(
                    servicer.RequestVote,
                    request_deserializer=raft__pb2.RequestVoteMessage.FromString,
                    response_serializer=raft__pb2.RequestVoteResponse.SerializeToString,
            ),
            'GetLeader': grpc.unary_unary_rpc_method_handler(
                    servicer.GetLeader,
                    request_deserializer=raft__pb2.EmptyMessage.FromString,
                    response_serializer=raft__pb2.GetLeaderResponse.SerializeToString,
            ),
            'SetKeyVal': grpc.unary_unary_rpc_method_handler(
                    servicer.SetKeyVal,
                    request_deserializer=raft__pb2.SetKeyValMessage.FromString,
                    response_serializer=raft__pb2.SetKeyValResponse.SerializeToString,
            ),
            'GetVal': grpc.unary_unary_rpc_method_handler(
                    servicer.GetVal,
                    request_deserializer=raft__pb2.GetValMessage.FromString,
                    response_serializer=raft__pb2.GetValResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'raft.Raft', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Raft(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def AppendEntries(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_unary(request_iterator, target, '/raft.Raft/AppendEntries',
            raft__pb2.AppendEntriesMessage.SerializeToString,
            raft__pb2.AppendEntriesResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def RequestVote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.Raft/RequestVote',
            raft__pb2.RequestVoteMessage.SerializeToString,
            raft__pb2.RequestVoteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetLeader(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.Raft/GetLeader',
            raft__pb2.EmptyMessage.SerializeToString,
            raft__pb2.GetLeaderResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SetKeyVal(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.Raft/SetKeyVal',
            raft__pb2.SetKeyValMessage.SerializeToString,
            raft__pb2.SetKeyValResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetVal(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/raft.Raft/GetVal',
            raft__pb2.GetValMessage.SerializeToString,
            raft__pb2.GetValResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
