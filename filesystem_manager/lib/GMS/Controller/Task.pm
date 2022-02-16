package GMS::Controller::Task;

use v5.14;

use strict;
use warnings;
use utf8;

our $AUTHORITY = 'cpan:gluesys';

use Mouse;
use namespace::clean -except => 'meta';

use Date::Parse qw/str2time/;
use Encode qw/decode_utf8/;
use JSON qw/decode_json/;
use POSIX qw/strftime/;
use Try::Tiny;
use Sys::Hostname::FQDN qw/short/;

use GMS::API::Return;
use GMS::Cluster::MDSAdapter;
use Girasole::Constants qw/:LEVEL/;

#---------------------------------------------------------------------------
#   Inheritances
#---------------------------------------------------------------------------
extends 'GMS::Controller';

#---------------------------------------------------------------------------
#   Attributes
#---------------------------------------------------------------------------
has mds => (
    is      => 'ro',
    isa     => 'Object',
    lazy    => 1,
    default => sub { GMS::Cluster::MDSAdapter->new(); },
);

#---------------------------------------------------------------------------
#   Methods
#---------------------------------------------------------------------------
sub task_list
{
    my $self   = shift;
    my $params = $self->req->json;

    my $numofrecs = $self->__get_numofrecs();
    my $pagenum   = $self->__get_pagenum();
    my $cond      = $self->__gen_task_cond();

    @{$cond}{qw/scope progress/} = (short(), {'<', 100});

    my $total = $self->mds->execute_dbi(
        db      => 'girasole',
        table   => 'Tasks',
        rs_func => 'search',
        rs_cond => $cond,
        rs_attr => {
            result_class => 'DBIx::Class::ResultClass::HashRefInflator',
        },
        func => 'count'
    );

    my $tasks;

    if (!defined($total))
    {
        api_status(
            level => 'ERROR',
            code  => TASK_LIST_FAILURE,
        );

        goto RETURN;
    }

    $tasks = $self->mds->execute_dbi(
        db      => 'girasole',
        table   => 'Tasks',
        rs_func => 'search',
        rs_cond => {scope => short()},
        rs_attr => {
            order_by     => {-desc => [qw/start finish/]},
            page         => $pagenum,
            rows         => $numofrecs,
            result_class => 'DBIx::Class::ResultClass::HashRefInflator',
        },
        func => 'all'
    );

    foreach my $task (@{$tasks})
    {
        map { $task->{ucfirst($_)} = delete($task->{$_}); } keys(%{$task});

        $task->{Level} = grs_strlevel(delete($task->{Level}));
        $task->{Start} = $task->{Start};
        $task->{Start}
            = strftime("%Y/%m/%d %T", localtime(delete($task->{Start})));
        $task->{Finish}
            = $task->{Finish}
            ? strftime("%Y/%m/%d %T", localtime(delete($task->{Finish})))
            : undef;

        try
        {
            $task->{Message} = decode_utf8($task->{Message});
            $task->{Details} = decode_json($task->{Details}, {utf8 => 1})
                if ($task->{Details} && $task->{Details} =~ m/^{.*}$/s);
        }
        catch
        {
            warn "[ERR] Unexpected error: @_";
        };
    }

    #api_status(
    #    level => 'INFO',
    #    code  => TASK_LIST_OK,
    #);

RETURN:
    $self->render(openapi => $tasks, total => $total);
}

sub task_count
{
    my $self   = shift;
    my $params = $self->req->json;

    my %retval = (
        info => 0,
        warn => 0,
        err  => 0,
    );

    my $cond = $self->__gen_task_cond();

    try
    {
        $cond->{Level} = grs_numlevel('INFO');

        $retval{info} = $self->mds->execute_dbi(
            db      => 'girasole',
            table   => 'Tasks',
            rs_func => 'search',
            rs_cond => $cond,
            rs_attr => {
                result_class => 'DBIx::Class::ResultClass::HashRefInflator'
            },
            func => 'count',
        );

        $cond->{Level} = grs_numlevel('WARNING');

        $retval{warn} = $self->mds->execute_dbi(
            db      => 'girasole',
            table   => 'Tasks',
            rs_func => 'search',
            rs_cond => $cond,
            rs_attr => {
                result_class => 'DBIx::Class::ResultClass::HashRefInflator'
            },
            func => 'count',
        );

        $cond->{Level} = grs_numlevel('ERROR');

        $retval{err} = $self->mds->execute_dbi(
            db      => 'girasole',
            table   => 'Tasks',
            rs_func => 'search',
            rs_cond => $cond,
            rs_attr => {
                result_class => 'DBIx::Class::ResultClass::HashRefInflator'
            },
            func => 'count',
        );
    }
    catch
    {
        warn "[ERR] Unexpected error: @_";
    };

RETURN:

    #api_status(
    #    level => 'INFO',
    #    code  => TASK_COUNT_OK
    #);

    $self->render(openapi => \%retval);
}

sub __get_numofrecs
{
    my $self = shift;

    my $numofrecs;

    if ($self->req->json)
    {
        $numofrecs = $self->req->json->{NumOfRecords};
    }
    elsif ($self->req->params)
    {
        $numofrecs = $self->req->params->to_hash()->{limit};
    }

    return $numofrecs // 30;
}

sub __get_pagenum
{
    my $self = shift;

    my $pagenum;

    if ($self->req->json)
    {
        $pagenum = $self->req->json->{PageNum};
    }
    elsif ($self->req->params)
    {
        $pagenum = $self->req->params->to_hash()->{page};
    }

    return $pagenum;
}

sub __gen_task_cond
{
    my $self = shift;

    my %args = ();

    if ($self->req->json)
    {
        %args = %{$self->req->json};
    }
    elsif ($self->req->params)
    {
        my $params = $self->req->params->to_hash();

        $args{From}     = $params->{from};
        $args{To}       = $params->{to};
        $args{Type}     = $params->{type};
        $args{Category} = $params->{category};
        $args{Level}    = $params->{level};
        $args{Scope}    = $params->{scope};
        $args{Message}  = $params->{message};
    }

    my $from     = $args{From};
    my $to       = $args{To};
    my $type     = $args{Type};
    my $category = $args{Category};
    my $level    = $args{Level};
    my $scope    = $args{Scope};
    my $message  = $args{Message};

    my %cond;

    if (defined($from) && $from !~ m/^\d+$/)
    {
        $from = str2time($from);
    }

    if (defined($to) && $to !~ m/^\d+$/)
    {
        $to = str2time($to);
    }

    if ((defined($from) && length($from))
        && (defined($to) && length($to)))
    {
        $cond{'-and'} = [
            start  => {'>=', $from},
            finish => {'<=', $to},
        ];
    }
    elsif (defined($from) && length($from))
    {
        $cond{start} = {'>=', $from};
    }
    elsif (defined($to) && length($to))
    {
        $cond{finish} = {'<=', $to};
    }

    if (defined($type) && length($type))
    {
        $cond{type} = {'like', "%$type%"};
    }

    if (defined($category) && length($category))
    {
        $cond{category} = {'like', "%$category%"};
    }

    if (defined($level) && length($level))
    {
        $cond{level} = grs_numlevel($level);
    }

    if (defined($scope) && length($scope))
    {
        $cond{scope} = {'like', "%$scope%"};
    }

    if (defined($message) && length($message))
    {
        $cond{message} = {'like', "%$message%"};
    }

    return \%cond;
}

__PACKAGE__->meta->make_immutable();
1;

=encoding utf8

=head1 NAME

GMS::Controller::Task - GMS API controller for task management features

=head1 SYNOPSIS

=head1 DESCRIPTION

=head1 COPYRIGHT AND LICENSE

Copyright 2015-2021. Gluesys Co., Ltd. All rights reserved.

=head1 SEE ALSO

=cut

