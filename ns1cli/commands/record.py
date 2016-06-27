#
# Copyright (c) 2014 NSONE, Inc.
#
# License under The MIT License (MIT). See LICENSE in project root.
#

from .base import BaseCommand, CommandException


class _record(BaseCommand):

    """
    Usage:
       ns1 record info ZONE DOMAIN TYPE
       ns1 record create ZONE DOMAIN TYPE [options] (ANSWER ...)
       ns1 record delete [-f] ZONE DOMAIN TYPE
       ns1 record link ZONE SOURCE_DOMAIN DOMAIN TYPE
       ns1 record set ZONE DOMAIN TYPE options
       ns1 record meta set ZONE DOMAIN TYPE KEY VALUE
       ns1 record meta remove ZONE DOMAIN TYPE KEY VALUE
       ns1 record answers ZONE DOMAIN TYPE [options] (ANSWER ...)
       ns1 record answer add ZONE DOMAIN TYPE ANSWER
       ns1 record answer remove ZONE DOMAIN TYPE ANSWER
       ns1 record answer meta set ZONE DOMAIN TYPE ANSWER KEY VALUE
       ns1 record answer meta remove ZONE DOMAIN TYPE ANSWER KEY

    Record operations. You may leave the zone name off of DOMAIN (do not end it
    with a period)

    Options:
       --ttl N                     TTL (Defaults to default zone TTL)
       --use-client-subnet BOOL    Set use of client-subnet EDNS option
                                   (Defaults to True on new records)
       --priority                  For MX records, the priority
       -f                          Force: override the write lock if one exists

    Record Actions:
       info          Get record details
       create        Create a new record, optionally with simple answers
       delete        Delete a record
       link          Create a linked record from an existing
       set           Set record properties, including record level meta data
       answers       Set one or more simple answers (no meta) for the record
       meta set      Set record level meta data
       meta remove   Remove record level meta data

    Answer Actions:
       add           Add an answer to a record
       remove        Remove an answer from a record
       meta set      Set meta data key/value to an answer. If it doesn't exist
                     it will be added
       meta remove   Remove meta data key from an answer

    Examples:
       record create test.com mail MX --priority 10 1.2.3.4
       record answer add test.com mail MX --priority 20 2.3.4.5

       record create test.com geo A --ttl 300 --use-client-subnet true 1.1.1.1
       record meta set test.com geo A priority 5
       record answers test.com geo A --ttl 300 1.2.3.4 6.7.8.9
       record answer add test.com geo A 3.3.3.3
       record answer meta set test.com geo A 1.2.3.4 georegion US-WEST
       record answer meta set test.com geo A 6.7.8.9 georegion US-EAST
       record answer meta set test.com geo A 3.3.3.3 georegion US-CENTRAL
    """

    SHORT_HELP = "Create, retrieve, update, and delete records in a zone"

    BOOL_OPTIONS = ('--use-client-subnet', )

    def run(self, args):
        self._record_api = self.nsone.records()
        self._zone = args['ZONE']
        self._domain = args['DOMAIN']
        self._type = args['TYPE']

        # if no dot in the domain name, assume we should add zone
        if self._domain.find('.') == -1:
            self._domain = '%s.%s' % (self._domain, self._zone)

        # order matters
        if args['info']:
            self.info()
        elif args['create']:
            self.create(args)
        elif args['delete']:
            self.delete(args)
        elif args['link']:
            self.link(args)
        elif args['set']:
            self.set(args)
        elif args['meta']:
            self.record_meta(args)
        elif args['answer']:
            self.answer(args)
        elif args['meta'] and args['answer']:
            self.answer_meta(args)
        elif args['answers']:
            self.set_answers(args)

    def _print_record_model(self, rdata):
        if self.isTextFormat():
            ans = rdata['answers']
            fil = rdata['filters']
            del rdata['answers']
            del rdata['filters']
            self.ppText(rdata)
            self.out('ANSWERS:')
            for a in ans:
                self.ppText(a, 4)
            if len(fil):
                self.out('FILTERS:')
                for a in fil:
                    self.ppText(a, 4)
        else:
            self.jsonOut(rdata)

    def create(self, args):
        self.checkWriteLock(args)
        kwargs = self._get_options(args)
        kwargs['answers'] = args['ANSWER']
        # XXX handle mx priority
        out = self._record_api.create(
            self._zone, self._domain, self._type, **kwargs)
        self._print_record_model(out)

    def delete(self, args):
        self.checkWriteLock(args)
        self._record_api.delete(self._zone, self._domain, self._type)

    def set(self, args):
        self.checkWriteLock(args)
        options = self._get_options(args)
        if 'use-client-subnet' in options:
            options['use_csubnet'] = options.pop('use-client-subnet')
        out = self._record_api.update(
            self._zone, self._domain, self._type, **options)
        self._print_record_model(out)

    def info(self):
        rdata = self._record_api.retrieve(self._zone, self._domain, self._type)
        self._print_record_model(rdata)

    def link(self, args):
        out = self._record_api.create(self._zone, self._domain, self._type,
                                      link=args['SOURCE_DOMAIN'], answers=[])
        self._print_record_model(out)

    def record_meta(self, args):
        self.checkWriteLock(args)
        current = self._record_api.retrieve(self._zone, self._domain, self._type)
        current['meta'][args['KEY']] = args['VALUE']
        rdata = self._record_api.update(self._zone, self._domain, self._type,
                                        meta=current['meta'])
        self._print_record_model(rdata)

    def set_answers(self, args):
        self.checkWriteLock(args)
        # XXX handle mx priority
        out = self._record_api.update(self._zone, self._domain, self._type,
                                      answers=args['ANSWER'])
        self._print_record_model(out)

    def answer_meta(self, args):
        self.checkWriteLock(args)
        # there is no rest api call to set meta without setting the entire
        # answer, so we have to retrieve it, alter it, and send it back
        answer = args['ANSWER'][0]
        current = self._record_api.retrieve(self._zone, self._domain, self._type)

        found = False
        for a in current['answers']:
            if a['answer'][0] == answer:
                a['meta'][args['KEY']] = args['VALUE']
                found = True
                break

        if not found:
            raise CommandException(self,
                                   '%s is not a current answer for this '
                                   'record' % answer)

        out = self._record_api.update(self._zone, self._domain, self._type,
                                      answers=current['answers'])
        self._print_record_model(out)

record = _record()
